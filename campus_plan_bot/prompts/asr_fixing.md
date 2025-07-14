Your task is to correct transcription errors in user inputs that were transcribed by an Automatic Speech Recognition (ASR) system. The primary goal is to identify and correct building numbers.

**Rules:**

1. **Output Format**: Your output must be a single building number or a comma-separated list of possible building numbers.
2. **No Building Number**: If you cannot find any potential building number in the input, or if no correction is needed, output the single word `EMPTY`.
3. **Valid Formats**: Corrected building numbers must conform to one of the following formats:
   * `XX.XX` (e.g., `50.32`, `03.45`)
   * `XXX` (e.g., `122`, `606`)
   * `XXXX` (e.g., `8011` which could also be `80.11`)
4. **Handling Ambiguity**: If a transcription is ambiguous, provide multiple potential corrections separated by commas.
5. **Focus**: Only correct the building numbers. Do not respond to the user's question or alter the rest of the text.

**Examples of Common ASR Errors and Correct Handling:**

**Case 1: Incorrect number structure**

* **User Input**: "Kannst du mit den Weg zu Gebaeude 0.3.45 zeigen."
* **Reasoning**: The format `X.X.XX` is invalid. This should be corrected to the valid `XX.XX` format.
* **Your Output**: `03.45`

---

**Case 2: Hyphenated numbers**

* **User Input**: "Man hat Gebaeude 800-3 geoeffnet."
* **Reasoning**: The hyphen is likely a transcription error. The user could mean `803` or `8003`. Both are valid formats, so provide both as possibilities.
* **Your Output**: `803, 8003`

---

**Case 3: Spelled-out numbers**

* **User Input**: "Wo ist Gebaeude fuenfzig Punkt vierunddreissig?"
* **Reasoning**: Convert the spelled-out number to the `XX.XX` format.
* **Your Output**: `50.34`

---

**Case 4: Numbers with spaces**

* **User Input**: "Wo ist Gebaeude 50 34?"
* **Reasoning**: The space should be a decimal point. There are no building numbers with just two digits!
* **Your Output**: `50.34`

---

**Case 5: Phonetic similarity (difficult case)**

* **User Input**: "Kann man derzeit ins Gebaeude 300 ziehen?"
* **Reasoning**: The word "ziehen" sounds like "zehn" (ten in German). The user might have meant `310`. This is an ambiguous case. It could also just be `300`. It's better to provide both.
* **Your Output**: `300, 310`

---

**Case 6: Missing decimal point in four-digit number**

* **User Input**: "Ist der Zugang zu Gebaeude 7011 ein hierher frei?"
* **Reasoning**: A four-digit number like `7011` is often a mis-transcription of the `XX.XX` format. The original number `7011` could also be valid but because it is already present in the input, you don't need to provide it.
* **Your Output**: `70.11`

---

**Case 7: No correction needed**

* **User Input**: "Wie komme ich zur Mensa?"
* **Reasoning**: No building number present.
* **Your Output**: `EMPTY`

---

**Case 8: Spelled-out integer**

* **User Input**: "Welche Adresse hat Gebäude einhundert und zwei?"
* **Reasoning**: Spelled-out numbers that represent an integer should be converted to their digit form (e.g., `XXX`).
* **Your Output**: `102`

---

**Case 9: Another spelled-out number example**

* **User Input**: "Wo ist Gebäude fünfzig Punkt vierunddreißig?"
* **Reasoning**: Convert the spelled-out number to the `XX.XX` format. This handles numbers containing "Punkt".
* **Your Output**: `50.34`

---

**Case 10: Spaced-out digits**

* **User Input**: "Wo ist Gebäude 2 5 9?"
* **Reasoning**: Digits separated by spaces should be concatenated to form a single valid building number. This is different from two-part numbers that might imply a decimal point.
* **Your Output**: `259`

---

Now, process the following user input:
`{asr_input}`

Remember your output must be a single building number or a comma-separated list of possible building numbers while considering the different cases.
