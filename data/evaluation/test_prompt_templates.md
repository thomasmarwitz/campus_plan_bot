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
- Das Gebäude hat die Adresse Y.
	- Default
- Ich kenne die Adresse von diesem Gebäude leider nicht.
	- If Y is not defined
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

**Variables:**
- X: building ID
- Y: category
**Prompt:** Was für ein Gebäude ist X?
**Answer cases:**
- Das Gebäude ist ein Y.
	- Default
- Ich habe leider keine Informationen dazu, um was für ein Gebäude es sich handelt.
	- If Y is not defined
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

**Variables:**
- X: building ID
- Y: rev_type
**Prompt:** Was befindet sich in Gebäude X?
**Answer cases:**
- In dem Gbäude befindet sich Y.
	- Default
- Ich habe keine Informationen dazu, was sich in dem Gebäude befindet.
	- If Y is not defined
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

**Variables:**
- X: building ID / building name (rev_name)
- Y: opening hours
**Prompt:** Was sind die Öffnungszeiten von Gebäude X?
**Answer cases:**
- Das Gebäude hat an Y geöffnet.
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
- Ja, das Gebäude ist rollstuhlgerecht. Es gibt Z.
	- If Y is yes. (Z only if there is a description)
- Das Gebäude ist teilweise rollstuhlgerecht.
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
- Das Gebäude öffnet in Y Minuten. / Das Gebäude ist noch Y Minuten geschlossen.
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
- Zu diesem Gebäude kenne ich leider keine Webseite.
	- If Y is not defined
- Zu diesem Gebäude habe ich leider keine Informationen.
	- If X is not in the database

### Some notes
- More templates are imaginable, but in order to keep complexity manageable we stick to the most important types of prompts for now
- It is possible to fill the template variables with a python script, but in order to receive a grammatically correct German sentence, some things (like articles, propositions) will have to be adjusted
- Rephrasing prompts generated from templates should be tested on a few manually created examples first
	- If it does not work well, the adjustment described above can be also used to rephrase the generated prompts manually
- The given answers are only exemplary and do not have to be rephrased since the system will not be evaluated on specific formulations. Important for evaluation are only the specified information and the correct answer case
	- The exemplary answers do currently not repeat the given information X. However in the evalution it can be assured the system "read back" the information it received, if that is the desired behaviour

### Open questions
- Are there any (edge) cases of formulations missing for the single turn prompts?
	- e.g. some unusual way that people might address a building or phrase a question
		- Commands instead of questions
- How can we formally define multi turn tests?
	- They are essentially a series of single turn prompts with some info left to context
		- e.g. Und was ist die Adresse? Ist es grade geöffnet?
	- Also consider non-standard multi turn question flow
		- e.g. correction of information by the user or asking questions in unusual order
