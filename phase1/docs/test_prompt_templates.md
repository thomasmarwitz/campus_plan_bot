The test prompts and expected answers are written in German because the system has to retrieve and process unusual German proper names. It is expected, that performance will be higher when using German as the system's internal language.

### Dummy template

**Variables:**
- X: some variable from the data
- Y: another variable from the data
**Prompt:** Lorem ipsum dolor sit amet, consetetur X sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna Y aliquyam erat, sed diam voluptua.
**Answer cases:**
- Lorem ipsum dolor sit amet, consetetur sadipscing elitr.
	- Default
- At vero eos et accusam et justo duo dolores et ea rebum.
	- If X has special value x

### Retrieve Static Information

**Variables:**
- X: building ID / building name (rev_name)
- Y: address
**Prompt:** Wo ist Gebäude X?
**Answer cases:**
- Das Gebäude X hat die Adresse Y.
	- Default
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

**Variables:**
- X: lecture hall name
- Y: building ID
**Prompt:** In welchem Gebäude befindet sich der X?
**Answer cases:**
- Der X befindet sich in Gebäude Y.
	- Default
- Diesen Hörsaal konnte ich leider nicht finden.
	- If X is not in the database

**Variables:**
- X: building ID
- Y: category
**Prompt:** Was für ein Gebäude ist X?
**Answer cases:**
- Das Gebäude X ist ein Y.
	- Default
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

**Variables:**
- X: building ID / building name (rev_name)
- Y: opening hours
**Prompt:** Was sind die Öffnungszeiten von Gebäude X?
**Answer cases:**
- Das Gebäude X hat an Y geöffnet.
	- Default
- Für dieses Gebäude kenne ich leider keine Öffnungszeiten.
	- If Y is not defined
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

**Variables:**
- X: building ID / building name (rev_name)
- Y: accessibility
- Z: wheelchair description
**Prompt:** Ist Gebäude X rollstuhlgerecht?
**Answer cases:**
- Ja, das Gebäude X ist rollstuhlgerecht. Es gibt Z.
	- If Y is yes. (Z only if there is a description)
- Das Gebäude X ist teilweise rollstuhlgerecht.
	- If Y is limited
- Nein, das Gebäude ist nicht rollstuhlgerecht.
	- If Y is no
- Zu diesem Gebäude habe ich leider keine Informationen zur Rollstuhgerechtikgeit.
	- If Y is not defined
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

### Current Time

**Variables:**
- X: building ID / building name (rev_name)
- Y: opening hours
**Prompt:** Ist Gebäude X grade geöffnet?
**Answer cases:**
- Ja, das Gebäude ist momentan geöffnet.
	- If current time is within Y
- Nein, das Gebäude ist momentan geschlossen.
	- If current time is not within Y
- Für dieses Gebäude kenne ich leider keine Öffnungszeiten.
	- If Y is not defined
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

**Variables:**
- X: building ID / building name (rev_name)
- Y: opening hours
**Prompt:** Wie lange ist Gebäude X noch geöffnet?
**Answer cases:**
- Das Gebäude schließt in Y Minuten. / Das Gebäude ist noch Y Minuten geöffnet.
	- If current time is within Y
- Das Gebäude ist momentan geschlossen.
	- If current time is not within Y
- Für dieses Gebäude kenne ich leider keine Öffnungszeiten.
	- If Y is not defined
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

**Variables:**
- X: building ID / building name (rev_name)
- Y: opening hours
**Prompt:** Wann öffnet Gebäude X?
**Answer cases:**
- Das Gebäude ist grade geöffnet.
	- If current time is within Y
- Das Gebäude öffnet um Y. / Das Gebäude öffnet in Y Minuten.
	- If current time is not within Y
- Für dieses Gebäude kenne ich leider keine Öffnungszeiten.
	- If Y is not defined
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

### Create Link for Navigation

**Variables:**
- X: building ID / building name (rev_name)
- Y: navigation link
**Prompt:** Wie komme ich zu Gebäude X? / Führe mich zu Gebäude X.
**Answer cases:**
- Mit diesem Link kannst du dich zu dem Gebäude führen lassen: Y.
	- Default
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

### Navigate to Website

**Variables:**
- X: building ID / building name (rev_name)
- Y: website
**Prompt:** Was ist die Webseite von Gebäude X? / Öffne die Webseite von Gebäude X.
**Answer cases:**
- Ich habe die Webseite für dich in deinem Browser geöffnet.
	- Default (programmatically opens Y)
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

### Some notes
- More templates are imaginable, but in order to keep complexity manageable we stick to the most important types of prompts for now
- It is possible to fill the template variables with a python script, but in order to receive a grammatically correct German sentence, some things (like article, propositions) will have to be manually adjusted
- Rephrasing prompts generated from templates should be tested on a few manually created examples first
	- If it does not work well, the manual adjustment described above can be also used to rephrase the generated prompts manually
- The given answers are only exemplary and do not have to be rephrased since the system will not be evaluated on specific formulations. Important for evaluation are only the specified information and the correct answer case

### Open questions
- Do we want the system to "read back" the information given to it by the user?
	- e.g. should it repeat the building name or ID when providing an answer
	- This might be important for evaluating system responses
- Are there any (edge) cases of formulations missing for the single turn prompts?
	- e.g. some unusual way that people might address a building or phrase a question
		- Commands instead of questions
- How can we formally define multi turn tests?
	- They are essentially a series of single turn prompts with some info left to context
		- e.g. Und was ist die Adresse? Ist es grade geöffnet?
	- Also consider non-standard multi turn question flow
		- e.g. correction of information by the user or asking questions in unusual order

