# Welcome to Campus-Plan-Bot
Campus-Plan-Bot helps its users navigate the KIT-Campus by providing information on buildings and navigation routes via a convenient natural language interface. It was built to improve the [old campus plan map](https://www.kit.edu/campusplan/), which allows users to look up the location of any KIT building by its (somewhat confusing) building ID, but does not provide any further information on buildings or allow users to conveniently navigate to them. Campus-Plan-Bot solves these issues by using an LLM to provide answers to the user's questions with RAG based on a hand-crafted dataset of KIT building information. The bot also allows for much more convenient navigation by utilizing external mapping services. It was built by [Thomas Marwitz](https://github.com/thomasmarwitz) and [Frederik Schittny](https://github.com/LunaNordin) in the context of a practical module at the [AI4LT](https://ai4lt.iar.kit.edu/english/index.php) research group at KIT.

https://github.com/user-attachments/assets/da0a091a-97e8-4990-aecf-6821dfeae5c6

## Features
Campus-Plan-Bot can help with orientation on the campus in several different ways. The most important features are:

#### Finding a Building
The buildings at KIT are often referenced with a building ID in the format `XX.XX`. To get the location of a building, simply ask Campus-Plan-Bot something like `Wo ist Gebäude 50.34?` (transl: Where is building 50.34?) to get the building's address. You can also refer to a building with a more colloquial name and ask the bot something like `Wo befindet sich die Mensa?` (transl: Where is the cafeteria?). Since these names are included in the bot's database, it can resolve them to the building's ID and tell you the location.

#### Navigation
Campus-Plan-Bot can quickly help you to navigate to any building. Simply tell it something like `Bring mich zu Gebäude 20.21.` (transl: Take me to building 20.21.) and the bot will generate and open a Google Maps link that will start a route from your current location to the building. If you have asked about the building before, you can take advantage of the bot's multi-turn capabilities and simply ask it `Und wie komme ich da hin?` (transl: And how do I get there?) to start a navigation.

#### Additional Building Information
Because Campus-Plan-Bot has access to a database containing additional information on buildings, it can answer questions like `Wann hat die Mensa geöffnet?` (transl: When is the cafeteria open?.). Because the bot has access to your device's current time, it can make its answer contextual and respond with `Die Mensa schließt in einer halben Stunde.` (transl: The cafeteria closes in half an hour.) rather than giving you a full set of opening hours for all days. Besides opening hours, the bot can also answer questions about buildings' wheelchair accessibility and open URLs associated with a building when asked about a building's website. Since the information is stored in an external database and is accessed by the LLM via RAG, it is easy to update any information or add additional data without the necessity for any re-training of the bot's internal model.

#### Convenient and Natural Interaction
Campus-Plan-Bot offers many convenient interface options for natural and easy interaction. Spoken user inputs can be transcribed either with a fast local ASR model or with a slower but more accurate remote ASR model. Repeated audio inputs can also be provided as an audio file (e.g. for testing and evaluation). Of course, the bot also offers the option to input queries as written text rather than relying on speech inputs. While the primary language of Campus-Plan-Bot is German to match the language of its internal database, there is an option to translate any system responses into different languages. For a natural interaction flow, the bot also supports multi-turn conversations. This allows users to leave information to the conversation context and ask follow-up questions without the need to repeat previously given information.

## System Architecture
In order to reach maximum performance in the defined tasks of providing building information and assisting with navigation, Campus-Plan-Bot processes user queries in multiple steps. Some of these steps are:
- fixing ASR transcription errors
- adding conversation context to multi-turn queries
- retrieving relevant information from the data corpus
- filtering the retrieved information to limit the system response to relevant information types
- generating a response to the user's query
- generating and opening links for navigation or building websites

These steps are carried out with a mixture of algorithmic approaches and the use of the internal LLM. To make the system more modular, the bot is built with a componentized architecture connected through interfaces. This makes it easy to add additional processing steps, modify existing ones, or upgrade the internal LLM to a more powerful or specialized model. More details on the system architecture can be found [here](PLANNING.md).

## Installation
The Campus-Plan-Bot project is developed using the Pixi package manager. If you are not familiar with the Pixi package manager and how to install it, you can have a look at the [Pixi documentation](https://pixi.sh/latest/). To install the dependencies needed in the `campus_plan_bot` repo, execute
```bash
pixi install
```
command after cloning the repository into a local folder. To make the repo an editable Python project and enable imports from arbitrary locations inside the `campus_plan_bot` folder, run:
```bash
pixi run postinstall
```
You can now run Campus-Plan-Bot by using the `pixi run` command and specify any command-line options:
```bash
pixi run python campus_plan_bot/cli.py <your command-line options here>
```
The current command-line options are:
- `--log-level` to choose how many system logs you want to have printed to the console (choose between `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`)
- `--input` to determine whether to use remote ASR (`ASR`), local ASR (`LOCAL_ASR`), or type in the user query with the keyboard (`TEXT`)
- `--token` to set the input token that is used to authenticate with the remote ASR server (the token is saved to the user preferences and only needs to be set when changed)
- `--file` to provide user audio query in the form of a local audio file rather than recording it with the system microphone

If you want to use the GUI rather than the CLI, you can start the app's backend by running:
```bash
pixi run uvicorn backend.app:app --reload
```
The GUI can then be reached under [http://127.0.0.1:8000/?lat=49.01025&amp;lon=8.41890](http://127.0.0.1:8000/?lat=49.01025&lon=8.41890) (you need to replace the `lat`and `lon` parameters with your current location for correct navigation).

## Deployment

You can deploy the Campus-Plan-Bot in a Docker container by building it with:
```
docker build --build-arg TOKEN="..." --build-arg INSTITUTE_URL="..." -t campus-plan-bot .
```
The parameter `INSTITUTE_URL` can be omitted if the default URL is still working. To run the bot, execute:
```
docker run -p 8000:8000 campus-plan-bot
```
An example deployment of Campus-Plan-Bot hosted by the AI4LT lab might be accessible in the coming weeks. We will update this README with a link when it becomes available.

## Evaluation
To evaluate the bot's performance throughout development, a large evaluation dataset was created. This consists of several hundred written queries with their respective expected answers based on the internal database. The queries cover all major system features and capabilities and are diverse in their formulation and phrasing. There are evaluation samples for both single-turn and multi-turn scenarios. Several hundred evaluation samples for different tasks and single- as well as multi-turn scenarios have been spoken in by the developers to allow for a full end-to-end evaluation of the system pipeline. The full evaluation dataset is available in this repository. More details on the evaluation process can be found [here](EVALUATION.md).

## Testing
While there are end-to-end tests available, these are mainly left to the evaluation of system updates and improvements. During development, pre-commit hooks were used to ensure code quality and consistency. More details on testing can be found [here](TESTING.md).


