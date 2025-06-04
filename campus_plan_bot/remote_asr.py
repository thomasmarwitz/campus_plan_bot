import argparse
import base64
import json
import os
import sys
import time
from threading import Thread

import click
import requests
from audio_recorder import AudioRecorder
from sseclient import SSEClient

from campus_plan_bot.interfaces import AutomaticSpeechRecognition


class RemoteASR(AutomaticSpeechRecognition):

    def get_audio_input(self, args):

        from streamadapter.ffmpeg_stream_adapter import FfmpegStream

        stream_adapter = FfmpegStream(
            volume=args.volume,
            repeat_input=False,
            ffmpeg_speed=args.ffmpeg_speed,
        )
        input = args.ffmpeg_input
        if input is None:
            print("The ffmpeg backend requires an url/file via the '-f' parameter")
            exit(1)
        elif not os.path.isfile(input) and not input.startswith("rtsp"):
            print("File", input, "does not exist")
            exit(1)

        stream_adapter.set_input(input)

        return stream_adapter

    def send_start(self, url, sessionID, streamID, api, token):
        data = {"controll": "START"}

        info = requests.post(
            url + "/" + api + "/" + sessionID + "/" + streamID + "/append",
            json=json.dumps(data),
            cookies={"_forward_auth": token},
        )
        if info.status_code != 200:
            print("ERROR in starting session")
            sys.exit(1)

    SAMPLE_RATE = 16000  # 16 kHz
    CHANNELS = 1  # Mono
    FRAME_SIZE = 960  # 20ms frames at 16kHz (common for Opus)

    def send_audio(
        self,
        last_end,
        audio_source,
        url,
        sessionID,
        streamID,
        api,
        token,
        raise_interrupt=True,
    ):
        chunk = audio_source.read()
        chunk = audio_source.chunk_modify(chunk)
        if raise_interrupt and len(chunk) == 0:
            raise KeyboardInterrupt()
        s = last_end
        e = s + len(chunk) / 32000

        data = {
            "b64_enc_pcm_s16le": base64.b64encode(chunk).decode("ascii"),
            "start": s,
            "end": e,
        }

        while True:
            try:
                res = requests.post(
                    url + "/" + api + "/" + sessionID + "/" + streamID + "/append",
                    json=json.dumps(data),
                    cookies={"_forward_auth": token},
                )
            except requests.exceptions.ConnectionError:
                print("Sending audio failed, retrying...")
                continue
            break
        if res.status_code != 200:
            print(res.status_code, res.text)
            print("ERROR in sending audio")
            sys.exit(1)

        return e

    def send_end(self, url, sessionID, streamID, api, token):
        data = {"controll": "END"}
        res = requests.post(
            url + "/" + api + "/" + sessionID + "/" + streamID + "/append",
            json=json.dumps(data),
            cookies={"_forward_auth": token},
        )
        if res.status_code != 200:
            print(res.status_code, res.text)
            print("ERROR in sending END message")
            sys.exit(1)

    def send_session(self, url, sessionID, streamID, audio_source, timeout, api, token):
        try:
            start_time = time.time()
            self.send_start(url, sessionID, streamID, api, token)

            last_end = 0
            while timeout is None or time.time() - start_time < timeout:
                last_end = self.send_audio(
                    last_end,
                    audio_source,
                    url,
                    sessionID,
                    streamID,
                    api,
                    token,
                    raise_interrupt=timeout is None,
                )
        except KeyboardInterrupt:
            pass

        time.sleep(1)
        self.send_end(url, sessionID, streamID, api, token)

    def read_text(self, url, sessionID, printing, output_file, start_time, api):

        messages = SSEClient(url + "/" + api + "/stream?channel=" + sessionID)
        for msg in messages:

            if msg.data is None or len(msg.data) == 0:
                messages.resp.close()
                break

            try:
                data = json.loads(msg.data)
            except json.decoder.JSONDecodeError:
                print(
                    "WARNING: json.decoder.JSONDecodeError (this may happen when running tts system but no video generation)"
                )
                continue

            if printing == -1:
                if "seq" in data:
                    self.transcript += data["seq"]
            elif printing == 0:
                if "controll" in data:
                    if data["controll"] == "INFORMATION":
                        s = f"{data['sender']}: PROPERTIES: {data[data['sender']]}"
                        print(s)
                        if output_file is not None:
                            with open(output_file, "a") as f:
                                f.write(s + "\n")
                    elif data["controll"] == "START":
                        s = f"{data['sender']}: START"
                        print(s)
                        if output_file is not None:
                            with open(output_file, "a") as f:
                                f.write(s + "\n")
                    elif data["controll"] == "END":
                        s = f"{data['sender']}: END"
                        print(s)
                        if output_file is not None:
                            with open(output_file, "a") as f:
                                f.write(s + "\n")
                else:
                    if "seq" in data:
                        s = f"{data['sender']}: OUTPUT {float(data['start']):.2f}-{float(data['end']):.2f}: {data['seq']}"
                        print(s)
                    elif "linkedData" in data and data["linkedData"]:
                        for k, v in data.items():
                            if type(v) is str and v.startswith("/ltapi"):
                                print("Received video or audio:", v)
                                break
                        s = None
                    if output_file is not None:
                        with open(output_file, "a") as f:
                            f.write(s + "\n")
            elif printing == 1:
                print(data)
                if output_file is not None:
                    with open(output_file, "a") as f:
                        f.write(str(data) + "\n")
            elif printing == 2:
                end_time = time.monotonic()
                received_time = end_time - start_time
                print(f"{received_time:.2f}▁{json.dumps(data)}")
                if output_file is not None:
                    with open(output_file, "a") as f:
                        f.write(f"{received_time:.2f}▁{json.dumps(data)}\n")

    def set_graph(self, args):

        d = (
            {"language": args.asr_properties["language"]}
            if "language" in args.asr_properties
            else {}
        )

        d["log"] = "False" if args.no_logging else "True"
        if args.no_textsegmenter:
            d["textseg"] = False
        d["error_correction"] = "None" if not args.use_error_correction else "True"
        if args.run_tts:
            d["tts"] = args.run_tts
        if args.generate_video:
            d["video"] = args.generate_video

        if args.summarize:
            d["summarize"] = True

        d["asr_prop"] = {
            k: v for k, v in args.asr_properties.items() if k != "language"
        }
        d["prep_prop"] = args.prep_properties
        d["textseg_prop"] = args.textseg_properties
        d["tts_prop"] = args.tts_properties
        d["lip_prop"] = args.video_properties

        res = requests.post(
            args.url + "/" + args.api + "/get_default_asr",
            json=json.dumps(d),
            cookies={"_forward_auth": args.token},
        )
        if res.status_code != 200:
            if res.status_code == 401:
                print(
                    "You are not authorized. Either authenticate with --url https://$username:$password@$server or with --token $token where you get the token from "
                    + args.url
                    + "/gettoken"
                )
            else:
                print(res.status_code, res.text)
                print("ERROR in requesting default graph for ASR")
            sys.exit(1)
        sessionID, streamID = res.text.split()

        # print("SessionId ",sessionID,"StreamID ",streamID)

        # graph = json.loads(
        #     requests.post(
        #         args.url + "/" + args.api + "/" + sessionID + "/getgraph",
        #         cookies={"_forward_auth": args.token},
        #     ).text
        # )
        # print("Graph:",graph)

        return sessionID, streamID

    def run_session(self, args, audio_source):
        sessionID, streamID = self.set_graph(args)

        start_time = time.monotonic()

        t = Thread(
            target=self.read_text,
            args=(
                args.url,
                sessionID,
                args.print,
                args.output_file,
                start_time,
                args.api,
            ),
        )
        t.daemon = True
        t.start()

        time.sleep(
            1
        )  # To make sure the SSEClient is running before sending the INFORMATION request

        self.send_session(
            args.url,
            sessionID,
            streamID,
            audio_source,
            args.timeout,
            args.api,
            args.token,
        )

        t.join()

    def transcribe(self, audio_path: str) -> str:
        """Create transcript for specified audio file."""

        args = argparse.Namespace(
            url="https://lt2srv-backup.iar.kit.edu",
            token="L3RAIM2vbTiTrGtIzt4Z5c2JFCZLCkboHOOAuPsba48=|1749644383|uolrr@student.kit.edu",
            input="ffmpeg",
            print=-1,
            output_file=None,
            ffmpeg_input=audio_path,
            volume=1.0,
            ffmpeg_speed=-1.0,
            no_logging=False,
            asr_properties={"language": "de"},
            no_textsegmenter=True,
            textseg_properties={},
            use_error_correction=False,
            prep_properties={},
            tts_properties={},
            video_properties={},
            timeout=None,
            run_tts=None,
            generate_video=None,
            summarize=False,
            api="webapi",
        )

        self.transcript = ""

        audio_source = self.get_audio_input(args)
        self.run_session(args, audio_source)

        return self.transcript.lstrip()

    def get_input(self) -> str:
        """Get audio input from the user and return the transcript."""

        filename = "campus_plan_bot/out.wav"
        recorder = AudioRecorder(filename)

        interrupt = recorder.record_audio()
        if interrupt:
            return "exit"
        else:
            self.transcribe(filename)
            print("\033[A                                                  \033[A")
            click.secho("You: ", fg="blue", nl=False)
            click.echo(f"{self.transcript}")
            return self.transcript


if __name__ == "__main__":
    asr = RemoteASR()
    asr.get_input()
