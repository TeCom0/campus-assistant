# Adjudication, run 1: 13 disagreements

Judge: mistral-large-2512. Decide each claim in adjudications_run1.json ("decision": supported / unsupported / no_claim, optional "note").
Your original labels are not changed.

---

## 1. academic_probation_en#2

**Your label:** unsupported

**Judge:** no_claim -> final no_claim (quote check: n/a (not supported))

**Claim** (source_line, checked against [5]):

> Under this status:

**Judge's quote:** (none)

**Judge's reason:** This is an introductory fragment and does not state a checkable fact.

**Question:** What happens if my GPA falls between 1.5 and 1.99?

<details><summary>Full answer</summary>

```text
If your semester GPA falls between **1.5 and 1.99**, the university places you on **academic probation**. Under this status:

* You may register for no more than **four courses** (up to **13 semester hours**) in the following regular semester.  
* To return to satisfactory standing you must achieve a **semester GPA of 2.00 or higher** by the end of that semester.  
* Summer or intersession performance does **not** count toward regaining satisfactory standing.  
* Academic probation is **not noted on your transcript**.

This information is taken from the AUI academic catalog. [5]
```

</details>

**Passages:**

[5] source: academic_catalog_2024_2025, pages: [121]

```text
time, a student may, after consulting with the advisor and the school coordinator, appeal to the
school dean for permission to take the course a third time.
Academic Probation
Undergraduate students are placed on academic probation if their GPA falls between 1.5 and 1.99.
This probationary status serves as a warning to students that their performance is below the level
required. Students on academic probation may not exceed four courses (up to 13 semester hours)
in the subsequent regular semester. To return to satisfactory standing at the end of this semester
requires a semester GPA of 2.00 or greater. Performance in a summer session or intersession does
not grant a return to a satisfactory standing. No notation of academic probation appears on the
transcript.
Unsatisfactory Standing
Undergraduate students are considered to have an unsatisfactory standing if their semester
GPA is less than 1.5. Students at this level must appeal and obtain special permission from
```


---

## 2. course_load_fr#3

**Your label:** unsupported

**Judge:** supported -> final supported (quote check: passed)

**Claim** (uncited, checked against all passages):

> C’est cette recommandation qui constitue la seule mention explicite d’une « sixième cours » dans le texte officiel.

**Judge's quote:** 'It is highly recommended that the scholarship beneficiary should take six courses per semester... In addition, any course dropped by the students must be validated by the Financial Aid Office'

**Judge's reason:** Passage [14] is the only explicit mention of a sixth course in the provided passages, aligning with the claim.

**Question:** Combien de cours puis-je suivre pendant un semestre normal, et quand ai-je droit à un sixième cours ?

<details><summary>Full answer</summary>

```text
Dans le catalogue de l’Université d’Akhawayn, la charge de travail habituelle d’un étudiant de premier cycle est de **5 cours par semestre** (soit environ 15 SCH = semestre de crédits).  

Le catalogue ne prévoit pas de limite supérieure stricte, mais il indique que **les boursiers** (ou bénéficiaires de bourses) sont **encouragés à suivre six cours par semestre** afin de respecter le calendrier de graduation. C’est cette recommandation qui constitue la seule mention explicite d’une « sixième cours » dans le texte officiel.  

> “Il est fortement recommandé que le bénéficiaire de la bourse prenne six cours par semestre et s’inscrive à au moins deux sessions d’été” [14].

Ainsi :

| Situation | Nombre de cours autorisés par semestre |
|-----------|----------------------------------------|
| Étudiant régulier (sans bourse) | 5 cours |
| Boursier (bénéficiaire d’une bourse AUI) | 6 cours (recommandé) |

Si vous êtes boursier, vous avez donc droit à un sixième cours dès le premier semestre où vous êtes inscrit sous le statut de bénéficiaire de la bourse. Pour toute situation particulière (ex. programmes spécifiques, crédits transférés, etc.), il est conseillé de vérifier auprès de votre conseiller académique ou du bureau des admissions, car les règles peuvent varier selon le programme ou le statut d’étudiant.
```

</details>

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [187, 188]

```text
PSY 2304 Psychology of Health
PSY 3302 Social/Organizational Psychology
PSY 3305 Interpersonal Relations and Conflict Resolution
PSY 3304 Industrial and Organizational Psychology
PSY 3306 Human Sexuality and Gender
PSY 3397 Language Acquisition
PSY 3395 Educational Psychology
PSY 3391 Forensic Psychology
PSY 3392 Psychology of Social Media
PSY 3393 Political Psychology
Course Code Course Name SCH
LDR 1201 and LDR 1202* 1st year program of Leadership Development Institute 4
LDR 2301 Personal Development for Leadership 3
LDR 4301 Leadership Practicum 3
HRD 4303 Leadership and Management 3
Al Akhawayn University
www.aui.ma
2024-
2025
188
Course Code Course Name SCH
COM 3306 Global Communication and Media Policy 3
GBU 3302 Legal Environment and Ethics 3
HRD 2301 or Legal Environment and Ethics for HRD or Ethics in
Professional Contexts
3
HRD 3302 Organizational Development and Change 3
HRD 4306 Organizational Behavior 3
MGT 3305 Conflict Management 3
MGT 3306 Management of Change 3
MGT 4308 Project Management 3
```


[2] source: academic_catalog_2024_2025, pages: [344, 345]

```text
SSC 5302 Multidisciplinary Research Design & Methods
SSC 5305 Gender in the Modern Middle East & North Africa
SSC 5310 Thesis Seminar1
Al Akhawayn University
www.aui.ma
2024-
2025
345
Optional Courses (12 SCH)
In addition to the six Core courses above, students in the NAMES program take six Optional courses from
the list below, which vary each academic year depending on student interests and faculty availability:
Total SCH requirement for the MA in NAMES: 30 SCH
Course Codes Course Name
HIS 5311 Modern Imperialism and its Culture
HIS 5312 Case Study in North African History
HIS 5325 Colonization and Decolonization in North Africa and the Middle East
HUM 5310 Amazigh History and Culture
HUM 5312 Popular Culture in North Africa
HUM 5323 Society & Politics in North African Literature and Film
HUM 5360 Issues in Contemporary Islam
INS 5361 Political Economy of North Africa and the Middle East
INS 5399 Special Topics in North African and Middle Eastern Studies
PSC 5350 Middle Eastern Politics
```


[3] source: academic_catalog_2024_2025, pages: [352, 353]

```text
cancel any course without sufficient student enrollment (between 6 and 16). Students registered for
courses that are not retained due to insufficient enrollment will be offered the option of enrolling in other
or subsequent Inter-session courses.
Concentration Courses (15 SCH)
Students are required to take an overall of five courses from their chosen Concentration (PR or VC&DD)
Course Code Course Name SCH
COM 5311 Design Thinking 3
COM 5312 Public Relations and Digital Media 3
COM 5313 Advanced Media and Communication
theory
3
PR or VC&DD concentration course
in Fall
3
Course Code Course Name SCH
SSC 5302 Multidisciplinary Research Design and 3
PR or VC&DD concentration course in Spring 3
PR or VC&DD concentration course in Spring 3
PR or VC&DD concentration course in Spring 3
Course Code Course Name SCH
COM 5391 or COM 5392 Thesis Seminar or Applied Practicum 3
PR or VC&DD concentration course in Summer 3
Al Akhawayn University
www.aui.ma
2024-
2025
353
Public Relations (PR) (15 SCH)
Fall
Spring
Summer
```


[4] source: academic_catalog_2024_2025, pages: [167, 168]

```text
General Education Requirements 40 SCH
SSAH Core 19 SCH
Major Core 33 SCH
Minor 15-18 SCH
Electives 9 SCH
Total SCH for the BSESS Major 116-119 SCH
Al Akhawayn University
www.aui.ma
2024-
2025
168
Psychology Major Core (33 SCH)
Required courses (24 SCH)
Additional optional courses (9 SCH)
Students must choose THREE courses from the following list:
Course Code Course Name
PSY 1301 Introduction to Psychology
PSY 1303 Clinical Psychology & Psychopathology
PSY 2302 Cognitive Sciences & Cognitive Psychology
PSY 2303 Developmental Psychology
PSY 2301 Cross-Cultural Psychology
PSY 3302 Social and Organizational Psychology
PSY 3399 Special Topics in Psychology
PSY 3306 Human Sexuality and Genders
Course Code Course Name
PSY 3304  Industrial/Organization Psychology
PSY 3305  Interpersonal Relations and Conflict Resolution
PSY 3308  Clinical Psychology
PSY 3391 Forensic Psychology
PSY 3392 Psychology of Social Media
PSY 3398 Special Topics in Clinical & Cognitive Psychology
```


[5] source: academic_catalog_2024_2025, pages: [351, 352]

```text
Course Code Course Name SCH
FAS 2210 Graduate Academic Skills*** 0
ENG 2301 Critical Thinking and Written
Communication
0
COM 2427 Art and Design 0
COM 3321 Moroccan Media and Society 0
Al Akhawayn University
www.aui.ma
2024-
2025
352
Communication and Digital Media Core (15 SCH)
Fall Semester (9 SCH required Core & 3 SCH concentration)
Spring Semester (3 SCH required Core & 9 SCH concentration)
Summer Session (3 SCH required Core & 9 SCH concentration)
Inter-session (January & May)
Optional courses may be offered during the January and May intersessions, which are two-week super-
intensive programs, designed for students to explore new special-topics courses. Students may choose,
in consultation with their academic advisors and/or Graduate Studies Coordinator, to take ONE inter-
session course that can substitute an optional MACDM course. Note that the Registrar’s Office will
cancel any course without sufficient student enrollment (between 6 and 16). Students registered for
```


[6] source: academic_catalog_2024_2025, pages: [188, 189]

```text
SSE and SBA for the following minors:
Minors (15 SCH):
-Minor in Business Administration for International Studies Major (15 SCH)
-Minor in Business Administration for Human Resource Development Majors (15 SCH)
-Minor in Business Administration for other SSAH majors (15 SCH)
-Minor in Computer Science (15 SCH)
-Minor in General Engineering (15 SCH)
-Minor in Data Analytics (15 SCH)
-Minor in Mathematics (15 SCH)
Al Akhawayn University
www.aui.ma
2024-
2025
189
SCHOOL OF SCIENCE AND ENGINEERING
Prof. Salah Al-Majeed,
Dean
Dr. Khalid Sendide,
Associate Dean
Prof. Abdelkrim Ouardaoui,
Student Academic Operations Coordinator
Prof. Houssaïn Kettani,
Subject Lead of Computer Science
Dr. Violetta Cavalli-Sforza,
Program Lead of the Bachelor of Science in Computer Science
Dr. Houda Chakiri,
Program Lead of the Master of Science in Big Data Analytics
Dr. Bouchaib Falah,
Program Lead of the Master of Science in Software Engineering
Prof. Mohammed Azzouz,
Subject Lead of Engineering
Dr. Rabie Zine,
```


[7] source: academic_catalog_2024_2025, pages: [213]

```text
Al Akhawayn University
www.aui.ma
2024-
2025
213
Basic Sciences (16 SCH)
Area 3: General Engineering (50 SCH)
Required Core Courses:
Area 4: Renewable Energy Major (18 SCH)
Required Major Courses (9 SCH)
Course Code Course Name
CHE 1401 Chemistry I
CHE 1402 Chemistry II
PHY 1401 Physics I
PHY 1402 Physics II
Course Code Course Name
RES 3311 Introduction to Physics of Energy
RES 4323 Power Distribution Systems and Smart Grids
RES 4325 Introduction to Renewable Energy Technologies and Sustainability
Course Code Course Name
CSC 1402 Computer Programming for Engineers
CSC 3308 Data Analysis (with Python)
EGR 2201 Introduction to Engineering and Design
EGR 2210 Computer Aided Engineering
EGR 2301 Statics
EGR 2302 Engineering Economics
EGR 2311 Dynamics
EGR 2402 Electric Circuits
EGR 3401 Fluid Mechanics
EGR 3302 Thermodynamics
EGR 3304 Materials Science
EGR 3305 Systems, Signals, and Control
EGR 3306 Engineering Instrumentation and Mechatronics
EGR 3331 Digital Design
EGR 4300 Internship
EGR 4402 Capstone Design
```


[8] source: academic_catalog_2024_2025, pages: [154, 155]

```text
ARA 1201
“Arabic Beginning” ARA
1202
“Arabic Intermediate”
ARA 1203
“Arabic Advanced” ARA
3299
“Special Topics in Arabic
for Non-Native Speakers”
3 French FRN 3210 “Advanced French Writing and Speaking
Skills”
2
Communication COM 1301 “Public Speaking”  3
Computer Science CSC 1300 “Introduction to Computers” 3
English ENG 1301 “English Composition”
+ ENG 2301 “Critical Thinking and Written Comm. ”
6
History or Political Science HIS 1301 “History of the Arab World” HUM 2302 “Intro.
To Islamic Civ. ”
4PSC 2301 “Comparative Political Systems
3
Al Akhawayn University
www.aui.ma
2024-
2025
155
Humanities LIT 2301 “Major Works of World Lit. ”
HUM 2306 “Comparative Religion”
PHI 2301 “Philosophical Thought”
PHI 2302 “History of ideas”
3
Art Appreciation & Creation ART 1301 “Music & Vocal Performance”
ART 1302 “Dance & Choreography”
ART 1303 “Painting and Sculpture”
ART 1304 “Drama and Theater”
ART 1305 “Art Appreciation and Creation”
ART 1399 “Special Topics in Art”
ART 3399 “Special Topics in Cultural Production”
```


[9] source: academic_catalog_2024_2025, pages: [177, 178]

```text
PSC 23011 Comparative Political Systems
Course Code Course Name
ECO 2310 Introduction to International Economics
GEO 1301 Introduction to Geography
HIS 3301 International History: 1914 to the Present
INS 3303 International Law
Al Akhawayn University
www.aui.ma
2024-
2025
178
Minor in Gender Studies  (15 SCH)
Students selecting this minor must take four Gender Studies courses and one additional elective from
among those offered in SSAH majors, including SSC 3398 Special Topics in Gender Studies.
Intended Learning Outcomes
Graduates of the Gender Studies Minor are expected to:
1. Include understanding of the history and development of feminist theories, including international
feminist theories.
2. Demonstrate extensive knowledge of gender-related issues in North Africa and the Middle East.
3. Be able to identify and analyze contemporary gender issues using feminist theories and methods.
4. Be able to write research papers and reports, including critical analytical academic papers.
Required Courses (12 SCH)
```


[10] source: academic_catalog_2024_2025, pages: [31, 32]

```text
Transfer Credit Maximums
For undergraduate programs, a maximum of 68 semester credits are transferable to AUI.
Applicants for the programs in the School of Science and Engineering who have attended «classes
préparatoires» may request credit for courses as transfer students. Each application will be considered
individually. Appropriate initial courses at AUI may be based on placement examinations, portfolio
analyses, interviews, and/or other assessments.
Visiting (Non-Degree Seeking) Students
Students in good standing at another college or university may study at AUI with visiting, non-degree
seeking status during the summer or semester. Visiting applicants wishing to convert to regular, degree-
seeking status after one or more semesters at AUI will be required to complete all the General Education
Al Akhawayn University
www.aui.ma
2024-
2025
32
requirements pertaining to their academic programs. Former AUI students do not automatically qualify
for visiting or non-degree status.
```


[11] source: academic_catalog_2024_2025, pages: [129]

```text
• Completion of the General Education requirements, including AUI language requirements (see
special section below);
•  major of at least 30 SCH, of which 12 must be at the advanced level and completed at AUI;
• If a minor is selected, it must consist of at least 15 SCH;
• A minimum of 60 SCH must be taken in residence at AUI. 24 of these must be at the advanced
level, of which at least 12 are taken in the major;
• A grade of at least C- in all courses counting toward the degree, exclusive of one elective. Major
programs may impose a more rigorous requirement for their majors;
• A minimum cumulative GPA of 2.00;
• A passing score on the Exit Test;
• Completion of all semester credit hours required towards the degree, of which 36 must be at the
advanced level;
• Satisfactory completion of all requirements specified for the degree;
• Application for graduation obtained through Enrollment Services by the specified deadline;
```


[12] source: academic_catalog_2024_2025, pages: [6]

```text
www.aui.ma
2024-
2025
SCHOOL OF HUMANITIES AND SOCIAL SCIENCES 152
Undergraduate Programs 153
BACHELOR OF ARTS IN INTERNATIONAL STUDIES 158
BACHELOR OF ARTS IN COMMUNICATION STUDIES (BACS) 162
BACHELOR OF SCIENCE IN ENVIRONMENTAL
STUDIES AND SUSTAINABILITY (124 SCH) 165
BACHLOR OD SCIENCE IN PSYCHOLOGY  167
BACHELOR OF SCIENCE IN
TERRITORIAL PLANNING AND MANAGEMENT (123 SCH) 170
BACHELOR OF SCIENCE IN HUMAN
RESOURCE DEVELOPMENT (124–123 SCH) 173
MINORS IN THE SCHOOL OF HUMANITIES
AND SOCIAL SCIENCES 176
MINOR IN INTERNATIONAL STUDIES (15 SCH) 177
MINOR IN GENDER STUDIES (15 SCH) 178
MINOR IN AFRICAN STUDIES (15 SCH) 179
MINOR IN HUMAN RESOURCE DEVELOPMENT (16 SCH) 180
MINOR IN NATIONAL HUMAN RESOURCE
DEVELOPMENT (16 SCH) 181
MINOR IN ORGANIZATIONAL STUDIES (16–15 SCH) 182
MINORS IN COMMUNICATION STUDIES (18–16 SCH) 184
MINOR IN PSYCHOLOGY (18–16 SCH) 186
SCHOOL OF SCIENCE AND ENGINEERING 189
Fulltime Faculty 190
Accreditation 190
Mission 190
SSE Undergraduate Programs 190
Bachelor of Science in Computer Science 192
```


[13] source: academic_catalog_2024_2025, pages: [293]

```text
Al Akhawayn University
www.aui.ma
2024-
2025
293
independence of events, random variables, cumulative distribution functions, density functions,
expectation, variance and covariance, independence of events and random variables, common discrete
and continuous distributions, Law of Large Numbers, the Central Limit Theorem, and an introduction to
descriptive statistics and sampling distributions.
MTH 2199, 2299, 2399, Special Topics in Mathematics
(Title to be assigned when offered) (3 ,2 ,1, SCH)
Prerequisites: SSE Approval
Variable lecture and/or laboratory hours
Special topics in mathematics courses may be taught by visiting or AUI faculty. This course is primarily
intended for freshmen and sophomores. Can be repeated (not to exceed 6 SCH).
MTH 4199, 4299, 4399, Special Topics in Mathematics
(Title to be assigned when offered) (3 ,2 ,1, SCH)
Prerequisites: Junior classification, SSE Approval
Variable lecture and/or laboratory hours
```


[14] source: academic_catalog_2024_2025, pages: [67]

```text
Scholarship Period
Undergraduate beneficiaries are eligible for AUI scholarship for a maximum of nine semesters (or eight
semesters plus two summer sessions), while graduate scholarships are allowed to use their scholarship
for a maximum of four semesters, including one semester at the Language Center. However,
extension for any extra semester including the summer session may be granted based on the scholarship
fund and on the beneficiary’s academic standing during the previous semesters at AUI.
Scholarships cover courses required for graduation only. It is highly recommended that the scholarship
beneficiary should take six courses per semester and enroll in at least two summer sessions. In addition,
any course dropped by the students must be validated by the Financial Aid Office.
If the student takes less than the recommended full-load, s/he should be aware that s/he runs the risk
of extending his/her time before graduation, therefore having to pay for additional or remaining courses.
```


---

## 3. course_load_fr#8

**Your label:** supported

**Judge:** unsupported -> final unsupported (quote check: n/a (not supported))

**Claim** (uncited, checked against all passages):

> Si vous êtes boursier, vous avez donc droit à un sixième cours dès le premier semestre où vous êtes inscrit sous le statut de bénéficiaire de la bourse.

**Judge's quote:** (none)

**Judge's reason:** Passage [14] states the recommendation but does not explicitly grant the 'right' to a sixth course from the first semester; it is a recommendation, not a guaranteed entitlement.

**Question:** Combien de cours puis-je suivre pendant un semestre normal, et quand ai-je droit à un sixième cours ?

<details><summary>Full answer</summary>

```text
Dans le catalogue de l’Université d’Akhawayn, la charge de travail habituelle d’un étudiant de premier cycle est de **5 cours par semestre** (soit environ 15 SCH = semestre de crédits).  

Le catalogue ne prévoit pas de limite supérieure stricte, mais il indique que **les boursiers** (ou bénéficiaires de bourses) sont **encouragés à suivre six cours par semestre** afin de respecter le calendrier de graduation. C’est cette recommandation qui constitue la seule mention explicite d’une « sixième cours » dans le texte officiel.  

> “Il est fortement recommandé que le bénéficiaire de la bourse prenne six cours par semestre et s’inscrive à au moins deux sessions d’été” [14].

Ainsi :

| Situation | Nombre de cours autorisés par semestre |
|-----------|----------------------------------------|
| Étudiant régulier (sans bourse) | 5 cours |
| Boursier (bénéficiaire d’une bourse AUI) | 6 cours (recommandé) |

Si vous êtes boursier, vous avez donc droit à un sixième cours dès le premier semestre où vous êtes inscrit sous le statut de bénéficiaire de la bourse. Pour toute situation particulière (ex. programmes spécifiques, crédits transférés, etc.), il est conseillé de vérifier auprès de votre conseiller académique ou du bureau des admissions, car les règles peuvent varier selon le programme ou le statut d’étudiant.
```

</details>

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [187, 188]

```text
PSY 2304 Psychology of Health
PSY 3302 Social/Organizational Psychology
PSY 3305 Interpersonal Relations and Conflict Resolution
PSY 3304 Industrial and Organizational Psychology
PSY 3306 Human Sexuality and Gender
PSY 3397 Language Acquisition
PSY 3395 Educational Psychology
PSY 3391 Forensic Psychology
PSY 3392 Psychology of Social Media
PSY 3393 Political Psychology
Course Code Course Name SCH
LDR 1201 and LDR 1202* 1st year program of Leadership Development Institute 4
LDR 2301 Personal Development for Leadership 3
LDR 4301 Leadership Practicum 3
HRD 4303 Leadership and Management 3
Al Akhawayn University
www.aui.ma
2024-
2025
188
Course Code Course Name SCH
COM 3306 Global Communication and Media Policy 3
GBU 3302 Legal Environment and Ethics 3
HRD 2301 or Legal Environment and Ethics for HRD or Ethics in
Professional Contexts
3
HRD 3302 Organizational Development and Change 3
HRD 4306 Organizational Behavior 3
MGT 3305 Conflict Management 3
MGT 3306 Management of Change 3
MGT 4308 Project Management 3
```


[2] source: academic_catalog_2024_2025, pages: [344, 345]

```text
SSC 5302 Multidisciplinary Research Design & Methods
SSC 5305 Gender in the Modern Middle East & North Africa
SSC 5310 Thesis Seminar1
Al Akhawayn University
www.aui.ma
2024-
2025
345
Optional Courses (12 SCH)
In addition to the six Core courses above, students in the NAMES program take six Optional courses from
the list below, which vary each academic year depending on student interests and faculty availability:
Total SCH requirement for the MA in NAMES: 30 SCH
Course Codes Course Name
HIS 5311 Modern Imperialism and its Culture
HIS 5312 Case Study in North African History
HIS 5325 Colonization and Decolonization in North Africa and the Middle East
HUM 5310 Amazigh History and Culture
HUM 5312 Popular Culture in North Africa
HUM 5323 Society & Politics in North African Literature and Film
HUM 5360 Issues in Contemporary Islam
INS 5361 Political Economy of North Africa and the Middle East
INS 5399 Special Topics in North African and Middle Eastern Studies
PSC 5350 Middle Eastern Politics
```


[3] source: academic_catalog_2024_2025, pages: [352, 353]

```text
cancel any course without sufficient student enrollment (between 6 and 16). Students registered for
courses that are not retained due to insufficient enrollment will be offered the option of enrolling in other
or subsequent Inter-session courses.
Concentration Courses (15 SCH)
Students are required to take an overall of five courses from their chosen Concentration (PR or VC&DD)
Course Code Course Name SCH
COM 5311 Design Thinking 3
COM 5312 Public Relations and Digital Media 3
COM 5313 Advanced Media and Communication
theory
3
PR or VC&DD concentration course
in Fall
3
Course Code Course Name SCH
SSC 5302 Multidisciplinary Research Design and 3
PR or VC&DD concentration course in Spring 3
PR or VC&DD concentration course in Spring 3
PR or VC&DD concentration course in Spring 3
Course Code Course Name SCH
COM 5391 or COM 5392 Thesis Seminar or Applied Practicum 3
PR or VC&DD concentration course in Summer 3
Al Akhawayn University
www.aui.ma
2024-
2025
353
Public Relations (PR) (15 SCH)
Fall
Spring
Summer
```


[4] source: academic_catalog_2024_2025, pages: [167, 168]

```text
General Education Requirements 40 SCH
SSAH Core 19 SCH
Major Core 33 SCH
Minor 15-18 SCH
Electives 9 SCH
Total SCH for the BSESS Major 116-119 SCH
Al Akhawayn University
www.aui.ma
2024-
2025
168
Psychology Major Core (33 SCH)
Required courses (24 SCH)
Additional optional courses (9 SCH)
Students must choose THREE courses from the following list:
Course Code Course Name
PSY 1301 Introduction to Psychology
PSY 1303 Clinical Psychology & Psychopathology
PSY 2302 Cognitive Sciences & Cognitive Psychology
PSY 2303 Developmental Psychology
PSY 2301 Cross-Cultural Psychology
PSY 3302 Social and Organizational Psychology
PSY 3399 Special Topics in Psychology
PSY 3306 Human Sexuality and Genders
Course Code Course Name
PSY 3304  Industrial/Organization Psychology
PSY 3305  Interpersonal Relations and Conflict Resolution
PSY 3308  Clinical Psychology
PSY 3391 Forensic Psychology
PSY 3392 Psychology of Social Media
PSY 3398 Special Topics in Clinical & Cognitive Psychology
```


[5] source: academic_catalog_2024_2025, pages: [351, 352]

```text
Course Code Course Name SCH
FAS 2210 Graduate Academic Skills*** 0
ENG 2301 Critical Thinking and Written
Communication
0
COM 2427 Art and Design 0
COM 3321 Moroccan Media and Society 0
Al Akhawayn University
www.aui.ma
2024-
2025
352
Communication and Digital Media Core (15 SCH)
Fall Semester (9 SCH required Core & 3 SCH concentration)
Spring Semester (3 SCH required Core & 9 SCH concentration)
Summer Session (3 SCH required Core & 9 SCH concentration)
Inter-session (January & May)
Optional courses may be offered during the January and May intersessions, which are two-week super-
intensive programs, designed for students to explore new special-topics courses. Students may choose,
in consultation with their academic advisors and/or Graduate Studies Coordinator, to take ONE inter-
session course that can substitute an optional MACDM course. Note that the Registrar’s Office will
cancel any course without sufficient student enrollment (between 6 and 16). Students registered for
```


[6] source: academic_catalog_2024_2025, pages: [188, 189]

```text
SSE and SBA for the following minors:
Minors (15 SCH):
-Minor in Business Administration for International Studies Major (15 SCH)
-Minor in Business Administration for Human Resource Development Majors (15 SCH)
-Minor in Business Administration for other SSAH majors (15 SCH)
-Minor in Computer Science (15 SCH)
-Minor in General Engineering (15 SCH)
-Minor in Data Analytics (15 SCH)
-Minor in Mathematics (15 SCH)
Al Akhawayn University
www.aui.ma
2024-
2025
189
SCHOOL OF SCIENCE AND ENGINEERING
Prof. Salah Al-Majeed,
Dean
Dr. Khalid Sendide,
Associate Dean
Prof. Abdelkrim Ouardaoui,
Student Academic Operations Coordinator
Prof. Houssaïn Kettani,
Subject Lead of Computer Science
Dr. Violetta Cavalli-Sforza,
Program Lead of the Bachelor of Science in Computer Science
Dr. Houda Chakiri,
Program Lead of the Master of Science in Big Data Analytics
Dr. Bouchaib Falah,
Program Lead of the Master of Science in Software Engineering
Prof. Mohammed Azzouz,
Subject Lead of Engineering
Dr. Rabie Zine,
```


[7] source: academic_catalog_2024_2025, pages: [213]

```text
Al Akhawayn University
www.aui.ma
2024-
2025
213
Basic Sciences (16 SCH)
Area 3: General Engineering (50 SCH)
Required Core Courses:
Area 4: Renewable Energy Major (18 SCH)
Required Major Courses (9 SCH)
Course Code Course Name
CHE 1401 Chemistry I
CHE 1402 Chemistry II
PHY 1401 Physics I
PHY 1402 Physics II
Course Code Course Name
RES 3311 Introduction to Physics of Energy
RES 4323 Power Distribution Systems and Smart Grids
RES 4325 Introduction to Renewable Energy Technologies and Sustainability
Course Code Course Name
CSC 1402 Computer Programming for Engineers
CSC 3308 Data Analysis (with Python)
EGR 2201 Introduction to Engineering and Design
EGR 2210 Computer Aided Engineering
EGR 2301 Statics
EGR 2302 Engineering Economics
EGR 2311 Dynamics
EGR 2402 Electric Circuits
EGR 3401 Fluid Mechanics
EGR 3302 Thermodynamics
EGR 3304 Materials Science
EGR 3305 Systems, Signals, and Control
EGR 3306 Engineering Instrumentation and Mechatronics
EGR 3331 Digital Design
EGR 4300 Internship
EGR 4402 Capstone Design
```


[8] source: academic_catalog_2024_2025, pages: [154, 155]

```text
ARA 1201
“Arabic Beginning” ARA
1202
“Arabic Intermediate”
ARA 1203
“Arabic Advanced” ARA
3299
“Special Topics in Arabic
for Non-Native Speakers”
3 French FRN 3210 “Advanced French Writing and Speaking
Skills”
2
Communication COM 1301 “Public Speaking”  3
Computer Science CSC 1300 “Introduction to Computers” 3
English ENG 1301 “English Composition”
+ ENG 2301 “Critical Thinking and Written Comm. ”
6
History or Political Science HIS 1301 “History of the Arab World” HUM 2302 “Intro.
To Islamic Civ. ”
4PSC 2301 “Comparative Political Systems
3
Al Akhawayn University
www.aui.ma
2024-
2025
155
Humanities LIT 2301 “Major Works of World Lit. ”
HUM 2306 “Comparative Religion”
PHI 2301 “Philosophical Thought”
PHI 2302 “History of ideas”
3
Art Appreciation & Creation ART 1301 “Music & Vocal Performance”
ART 1302 “Dance & Choreography”
ART 1303 “Painting and Sculpture”
ART 1304 “Drama and Theater”
ART 1305 “Art Appreciation and Creation”
ART 1399 “Special Topics in Art”
ART 3399 “Special Topics in Cultural Production”
```


[9] source: academic_catalog_2024_2025, pages: [177, 178]

```text
PSC 23011 Comparative Political Systems
Course Code Course Name
ECO 2310 Introduction to International Economics
GEO 1301 Introduction to Geography
HIS 3301 International History: 1914 to the Present
INS 3303 International Law
Al Akhawayn University
www.aui.ma
2024-
2025
178
Minor in Gender Studies  (15 SCH)
Students selecting this minor must take four Gender Studies courses and one additional elective from
among those offered in SSAH majors, including SSC 3398 Special Topics in Gender Studies.
Intended Learning Outcomes
Graduates of the Gender Studies Minor are expected to:
1. Include understanding of the history and development of feminist theories, including international
feminist theories.
2. Demonstrate extensive knowledge of gender-related issues in North Africa and the Middle East.
3. Be able to identify and analyze contemporary gender issues using feminist theories and methods.
4. Be able to write research papers and reports, including critical analytical academic papers.
Required Courses (12 SCH)
```


[10] source: academic_catalog_2024_2025, pages: [31, 32]

```text
Transfer Credit Maximums
For undergraduate programs, a maximum of 68 semester credits are transferable to AUI.
Applicants for the programs in the School of Science and Engineering who have attended «classes
préparatoires» may request credit for courses as transfer students. Each application will be considered
individually. Appropriate initial courses at AUI may be based on placement examinations, portfolio
analyses, interviews, and/or other assessments.
Visiting (Non-Degree Seeking) Students
Students in good standing at another college or university may study at AUI with visiting, non-degree
seeking status during the summer or semester. Visiting applicants wishing to convert to regular, degree-
seeking status after one or more semesters at AUI will be required to complete all the General Education
Al Akhawayn University
www.aui.ma
2024-
2025
32
requirements pertaining to their academic programs. Former AUI students do not automatically qualify
for visiting or non-degree status.
```


[11] source: academic_catalog_2024_2025, pages: [129]

```text
• Completion of the General Education requirements, including AUI language requirements (see
special section below);
•  major of at least 30 SCH, of which 12 must be at the advanced level and completed at AUI;
• If a minor is selected, it must consist of at least 15 SCH;
• A minimum of 60 SCH must be taken in residence at AUI. 24 of these must be at the advanced
level, of which at least 12 are taken in the major;
• A grade of at least C- in all courses counting toward the degree, exclusive of one elective. Major
programs may impose a more rigorous requirement for their majors;
• A minimum cumulative GPA of 2.00;
• A passing score on the Exit Test;
• Completion of all semester credit hours required towards the degree, of which 36 must be at the
advanced level;
• Satisfactory completion of all requirements specified for the degree;
• Application for graduation obtained through Enrollment Services by the specified deadline;
```


[12] source: academic_catalog_2024_2025, pages: [6]

```text
www.aui.ma
2024-
2025
SCHOOL OF HUMANITIES AND SOCIAL SCIENCES 152
Undergraduate Programs 153
BACHELOR OF ARTS IN INTERNATIONAL STUDIES 158
BACHELOR OF ARTS IN COMMUNICATION STUDIES (BACS) 162
BACHELOR OF SCIENCE IN ENVIRONMENTAL
STUDIES AND SUSTAINABILITY (124 SCH) 165
BACHLOR OD SCIENCE IN PSYCHOLOGY  167
BACHELOR OF SCIENCE IN
TERRITORIAL PLANNING AND MANAGEMENT (123 SCH) 170
BACHELOR OF SCIENCE IN HUMAN
RESOURCE DEVELOPMENT (124–123 SCH) 173
MINORS IN THE SCHOOL OF HUMANITIES
AND SOCIAL SCIENCES 176
MINOR IN INTERNATIONAL STUDIES (15 SCH) 177
MINOR IN GENDER STUDIES (15 SCH) 178
MINOR IN AFRICAN STUDIES (15 SCH) 179
MINOR IN HUMAN RESOURCE DEVELOPMENT (16 SCH) 180
MINOR IN NATIONAL HUMAN RESOURCE
DEVELOPMENT (16 SCH) 181
MINOR IN ORGANIZATIONAL STUDIES (16–15 SCH) 182
MINORS IN COMMUNICATION STUDIES (18–16 SCH) 184
MINOR IN PSYCHOLOGY (18–16 SCH) 186
SCHOOL OF SCIENCE AND ENGINEERING 189
Fulltime Faculty 190
Accreditation 190
Mission 190
SSE Undergraduate Programs 190
Bachelor of Science in Computer Science 192
```


[13] source: academic_catalog_2024_2025, pages: [293]

```text
Al Akhawayn University
www.aui.ma
2024-
2025
293
independence of events, random variables, cumulative distribution functions, density functions,
expectation, variance and covariance, independence of events and random variables, common discrete
and continuous distributions, Law of Large Numbers, the Central Limit Theorem, and an introduction to
descriptive statistics and sampling distributions.
MTH 2199, 2299, 2399, Special Topics in Mathematics
(Title to be assigned when offered) (3 ,2 ,1, SCH)
Prerequisites: SSE Approval
Variable lecture and/or laboratory hours
Special topics in mathematics courses may be taught by visiting or AUI faculty. This course is primarily
intended for freshmen and sophomores. Can be repeated (not to exceed 6 SCH).
MTH 4199, 4299, 4399, Special Topics in Mathematics
(Title to be assigned when offered) (3 ,2 ,1, SCH)
Prerequisites: Junior classification, SSE Approval
Variable lecture and/or laboratory hours
```


[14] source: academic_catalog_2024_2025, pages: [67]

```text
Scholarship Period
Undergraduate beneficiaries are eligible for AUI scholarship for a maximum of nine semesters (or eight
semesters plus two summer sessions), while graduate scholarships are allowed to use their scholarship
for a maximum of four semesters, including one semester at the Language Center. However,
extension for any extra semester including the summer session may be granted based on the scholarship
fund and on the beneficiary’s academic standing during the previous semesters at AUI.
Scholarships cover courses required for graduation only. It is highly recommended that the scholarship
beneficiary should take six courses per semester and enroll in at least two summer sessions. In addition,
any course dropped by the students must be validated by the Financial Aid Office.
If the student takes less than the recommended full-load, s/he should be aware that s/he runs the risk
of extending his/her time before graduation, therefore having to pay for additional or remaining courses.
```


---

## 4. fulbright_fr#1

**Your label:** no_claim

**Judge:** supported -> final unsupported (quote check: FAILED -- quote not found in these passages)

**Claim** (uncited, checked against all passages):

> Je n’ai pas trouvé d’information dans les documents officiels de l’AUI concernant la procédure spécifique pour postuler à la bourse Fulbright via l’université.

**Judge's quote:** 'Je n’ai pas trouvé d’information dans les documents officiels de l’AUI...'

**Judge's reason:** The claim is directly stated in the answer, and none of the provided passages mention the Fulbright scholarship or its application procedure via AUI.

**Question:** Comment postuler à la bourse Fulbright via l'AUI ?

<details><summary>Full answer</summary>

```text
Je n’ai pas trouvé d’information dans les documents officiels de l’AUI concernant la procédure spécifique pour postuler à la bourse Fulbright via l’université. Il est possible que ce type de bourse soit géré directement par le programme Fulbright ou par l’Office des programmes internationaux de l’AUI, mais je ne dispose pas de sources documentaires précises à ce sujet. Je vous conseille de contacter le **Bureau des programmes internationaux** (Office of International Programs) de l’AUI ou de consulter le site officiel de Fulbright pour obtenir les étapes exactes de candidature.
```

</details>

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [67]

```text
mittee with a distinction of at least “Assez Bien” in the “Licence, ” an equivalent for the French sys-
tem, or a CGPA of 3.25/4.00 for applicants with an American type degree;
• Superior rating at the scholarship and admission interview where applicable.
A combination of these elements is used to rank scholarship applicants and determine the type of
scholarships to be offered. Scholarships vary from 10% to 60% of tuition.
Procedure
Undergraduate candidates can apply for a scholarship by completing the online scholarship appli-
cation while graduate applicants can complete the graduate scholarship form downloadable from
the website before the established deadline. The scholarship application process is mainly open for fall
semesters to undergraduate students and for fall and spring semesters to graduates.
Scholarship Period
Undergraduate beneficiaries are eligible for AUI scholarship for a maximum of nine semesters (or eight
```


[2] source: academic_catalog_2024_2025, pages: [28]

```text
www.aui.ma
2024-
2025
28
Application Deadlines
Admission of students to academic programs at AUI is competitive, allowing for the selection of the best
candidates with the greatest potential for success in their studies. The faculty is composed of teachers/
researchers who have demonstrated academic and pedagogical prowess.
In order to ensure openness of the University to the world and to promote a healthy, scientific collabora-
tion and understanding among people, a portion of the faculty consists of full- or part-time appointments
of international teachers/researchers renowned in their fields. Likewise, AUI welcomes international stu-
dents who satisfy the regular selection criteria for admission.
Applicants are strongly advised to apply early to ensure timely processing.
Please refer to the University website for a detailed calendar.
Fall Semester:
Spring Semester:
Freshman Transfer Visiting Graduate
Moroccan May 31 April 30 April 30 May 31
International April 30 April 30 April 30 May 31
```


[3] source: academic_catalog_2024_2025, pages: [120]

```text
• Students may not withdraw from any course.
• A failing grade means D, F , or WF .
Probation Regulations and Procedures
These regulations and procedures are published to assist students by providing information
essential to meeting University standards and to ensure progress when students perform at a low
academic level. Every student is responsible for knowing these regulations.
Repeat Policy
All courses taken at AUI, whether passed or failed, remain a permanent part of the student’s record.
Semester of Unsatisfactory
Performance
Student Performance Freshman Committee
Decision
Enrollment Summer
First Semester
on At-Risk List
SGPA < 2.0 Warning Allowed
SGPA < 2.0
and failing 1-
2 courses
SGPA < 2.0
and failing 3 or more courses
Strong Warning Not Allowed
If decision was Warning and... SGPA ≥ 2.0 Under Watch Allowed
SGPA < 2.0 Last Chance Not Allowed
SGPA ≥ 2.0 Under Watch Allowed
If Decision
was Strong Warning and...
SGPA < 2.0 Dismissal
(may appeal)
Not Allowed
SGPA ≥ 2.9 Under Watch Allowed
```


[4] source: academic_catalog_2024_2025, pages: [5]

```text
REQUIRED DOCUMENTS FOR FINANCIAL AID 50
APPLICATION DEADLINES   52
TYPES OF FINANCIAL AID OFFERED AT AUI 52
AUI Scholarships for New Students  66
AUI Scholarships for Continuing Students  74
STUDENT SUPPORT    75
Center for Learning Excellence (CLE)  75
Student Services    77
Student Life    78
Athletics     81
Student Housing    85
Student Conduct    86
Campus Store    87
Counseling    87
Health Center    88
Dining Services    88
Computer and Email Support   88
ACADEMIC RESOURCES  92
Mohammed VI Library  92
Advising for Freshmen  93
The office of Employability & Entrepreneurship  93
Office of Academic Support and Progress (OASP)  94
Office of International Programs  94
REGISTRATION REGULATIONS  97
Academic Advising  97
Preregistration  97
Regular Registration  97
Late Registration  97
Class Day  97
Semester Credit Hour  97
Prerequisites  98
Academic Calendar  98
Enrollment Certificates  98
Student Transcripts  98
Certificate of Completion  98
Name Change of Current Students  99
Death of a Current Student  99
```


[5] source: academic_catalog_2024_2025, pages: [143, 144]

```text
ECO 2301 Microeconomics
ECO 2302 Macroeconomics
FIN 3301 Principles of Finance
GBU 2301 Business Statistics
GBU 3302 Business Law and Ethics
GBU 3203 Enterprises, Markets, and the Moroccan Economy
GBU 3311 Quantitative Methods in Business
GBU 4101 Transitioning To The Business World
INT 4001 Internship Field Work
INT 4301 Internship
MGT 3301 Principles of Management
MGT 3302 Entrepreneurship
MGT 4301 Capstone Course: Business Policy and Corporate Strategy
MGT 4303 Operations Management
MIS 3301 Management Information Systems
MKT 3301 Principles of Marketing
Al Akhawayn University
www.aui.ma
2024-
2025
144
Course Code Course Name
FIN 3302 Money and Banking
FIN 3303 Corporate Financial Management
FIN 3305 Introduction to Islamic Banking and Finance
FIN 3306 Corporate Governance
FIN 3307 Financial Reporting and Analysis
FIN 3399 Special Topics in Finance
FIN 4304 International Finance
FIN 4305 Financial Intermediation
FIN 4306 Financial Investments and Securities Analysis
```


[6] source: academic_catalog_2024_2025, pages: [60]

```text
registration, this discount is applicable only once.
Moreover, undergraduate or graduate students combining scholarships and financial aid can be-
nefit only from either their scholarship or their grant on a prorated basis.
Moreover, if the undergraduate or the graduate student obtains a grade of «W» or « WP» or « WF»
or «F» in all courses at the end of any semester, s/he will be automatically placed on financial aid
suspension for the following semester.
Students on financial aid probation or suspension may, with proper authorization, attend the AUI
summer session at their own expense. However, students will not regain satisfactory academic
standing by attending summer session. Neither will they be granted eligibility for financial aid for
the following semester, regardless of their summer results.
Financial Aid Renewal Policy for Undergraduate Students
Semester GPA Financial Aid forthefollowing semester
≥ 2.00/4.00 Good standing: grant is maintained%
```


[7] source: academic_catalog_2024_2025, pages: [16]

```text
and the arts, as well as assisting with the emancipation and prosperity of modern nations. We promote
these while maintaining a goal of preserving our assets and consolidating our country’s calling as a land
of encounter, liberty, and tolerance - a global objective in which our Kingdom takes deep pride.
In 1995, our monarch, King Hassan II, seeking to enrich our educational system through the establishment
of a new university, challenged the founders to create an organizational, pedagogical, and scientific
structure inspired from the most effective models. AUI, modeled in its administrative, pedagogical,
and academic organization on the American university system, is meant to be a forum for creativity
and human progress in all fields of knowledge, as well as an avenue for cooperation and understanding
among peoples and civilizations.
Since its inception, the University has manifested its wish to contribute to the training of highly qualified
```


[8] source: academic_catalog_2024_2025, pages: [60]

```text
or Spring semesters are placed on financial aid probation for the following semester. Students
unable to regain satisfactory academic standing (by taking at least 12 credits or 4 courses for un-
dergraduate and 9 credits OR 3 courses graduates) at the conclusion of the probationary semester
will be placed on financial aid suspension until they satisfy the semester grade point average re-
quirement. If, on the other hand, students obtain a semester grade point average below 1.50/4.00
for undergraduates and 2.50/4.00 for graduates, they will lose their eligibility for financial aid for
the following semester.
The financial aid amount should not exceed the cost of any credit left for both undergraduate and
graduate students mainly during their last semester(s) at AUI (such as the one credit left for conti-
nuous registration, or the three credits left for an internship). In case of one credit for continuous
registration, this discount is applicable only once.
```


---

## 5. graduation_honors_en#2

**Your label:** unsupported

**Judge:** supported -> final supported (quote check: passed)

**Claim** (source_line, checked against [1]):

> This is the highest honors level listed in the academic catalog.

**Judge's quote:** '3.25 - 3.49 Cum Laude (with honors)\n3.50 - 3.64 Magna Cum Laude (with high honors)\n3.65 - 4.00 Summa Cum Laude (with highest honors)'

**Judge's reason:** The passage lists summa cum laude as the highest honors level.

**Question:** What GPA do I need to graduate summa cum laude?

<details><summary>Full answer</summary>

```text
To graduate **summa cum laude** at Al Akhawayn University, you need a cumulative GPA of **3.65 or higher** (up to 4.00). This is the highest honors level listed in the academic catalog.  

[1]
```

</details>

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [118, 119]

```text
honors. This honor is noted on the student’s diploma. Honors are awarded based on the following
GPA scale:
Diploma Delivery
Students who have fulfilled all academic requirements towards their degrees and have received
final clearance from the Office of Business Services will receive their diplomas from Enrollment
Services soon after the graduation ceremony.
3.25 - 3.49 Cum Laude (with honors)
3.50 - 3.64 Magna Cum Laude (with high honors)
3.65 - 4.00 Summa Cum Laude (with highest honors)
Al Akhawayn University
www.aui.ma
2024-
2025
119
The Diploma is issued only once.
Diplomas delivered to undergraduate students bear the official date of grade submission to the
Office of the Registrar as published in the catalog. For graduate students, the diploma bears the
date of the completion of the last requirement, which is usually the thesis defense. Should there
be another requirement after the defense, the date of completion of that requirement is the official
```


---

## 6. instructor_en#1

**Your label:** no_claim

**Judge:** supported -> final supported (quote check: passed)

**Claim** (uncited, checked against all passages):

> I’m sorry, but I couldn’t find any information in the available AUI documents that lists the instructor for CSC 3326 for the next semester.

**Judge's quote:** 'CSC 3326 Database Systems (3 SCH)... The course covers the design and implementation of Relational databases...'

**Judge's reason:** The passages only provide course descriptions, prerequisites, and general catalog information, with no mention of teaching assignments or instructors for any course.

**Question:** Who is teaching CSC 3326 next semester?

<details><summary>Full answer</summary>

```text
I’m sorry, but I couldn’t find any information in the available AUI documents that lists the instructor for CSC 3326 for the next semester. The catalog entries provide course descriptions and prerequisites but do not include teaching assignments. If you need the current instructor, I recommend checking the semester’s course schedule or contacting the Computer Science department directly.
```

</details>

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [240]

```text
CSC 3346 Data Engineering and Visualization (3 SCH)
Prerequisites: CSC 3326
3 lecture hours
This course covers two independent, but complementary parts, namely data engineering and data
visualization. In the first part we will cover data engineering, which is a prerequisite to any data science/
analytics project. We will explore various ways in building and maintaining data architectures for ingestion
and processing, as well as ways for ensuring that there is uninterrupted flow/pipeline of data between
servers and analytics applications. This includes moving data around, integrating new data sources,
building data collection pipelines, among various other things using ETL (Extract, Transform and Load)
tools.
The second part will cover the art and science of turning data into readable graphics. We will explore how
to design and create data visualizations based on data available and business objectives. This includes
```


[2] source: academic_catalog_2024_2025, pages: [245]

```text
e-commerce application for educational purposes.
CSC 4351 Statistical Analysis (3 SCH)
Prerequisites: MTH 3301
3 lecture hours
This course provides statistical methods and tools for analytics, helping students in applying them for
purposes of data analysis, hypothesis testing, and building prediction and forecasting models.
CSC 4352 Big Data Analytics (3 SCH)
Prerequisites: CSC 3331
3 lecture hours
This course provides concepts and tools for building and adapting data-oriented analytical models based
on massive data of different formats, using the parallel and distributed programming paradigms and data
structures.
Economics (ECO)
ECO 1300 Introduction to Economics (3 SCH)
3 lecture hours
This course introduces students to the essentials of both microeconomics and macroeconomics.
Topics in microeconomics include supply and demand, price elasticity, producer and consumer choices,
and market structures. The macroeconomic section of the course will tackle gross domestic product,
```


[3] source: academic_catalog_2024_2025, pages: [243]

```text
Prerequisites: CSC 3326, CSC 3351
3 lecture hours
This course provides theoretical knowledge about, and practical skills in advanced programming
paradigms. It builds on the background acquired in introductory programming courses and other
prerequisite courses to tackle programming models used in professional, enterprise-grade software
development. Covered topics are organized into five parts, where each build on previous ones:
• Part I. Programming for communication: Client/server model and programming
• Part II. Programming for integration: Service-oriented model and programming
• Part III. Programming for performance: Multithreaded and asynchronous programming
• Part IV . Programming for extensibility: Functional and reactive programming
• Part V . Programming for scalability: Distributed and parallelized programming. This course adopts the 3
most popular programming languages: Python, JavaScript, and Java. Each time, it uses the most suitable
```


[4] source: academic_catalog_2024_2025, pages: [241]

```text
Prerequisites: CSC 3326
3 lecture hours
The course covers some advanced issues in database systems, including database storage, indexing and
query processing, etc. Significant focus is placed on data warehouse design and architecture, including
the fundamental concepts of dimensional modeling, covering star schemas and OLAP cubes. ETL and
analytical querying and reporting for better decision-support are addressed, using case study analysis
and project design.
CSC 3351 Operating Systems (3 SCH)
Prerequisites: CSC 2305
3 lecture hours
This course introduces students to fundamental concepts of operating systems. It emphasizes structures,
key design issues, as well as the fundamental principles behind modern operating systems. It covers
concurrency, scheduling, memory and device management, file systems, and scripting. The course uses
implementations of Unix-like and Windows systems to illustrate some concepts.
CSC 3357 Object Oriented Design
Prerequisites: CSC 2306 and Junior classification
```


[5] source: academic_catalog_2024_2025, pages: [240]

```text
as state of the art IoT cloud platforms and architectural patterns. As IoT is a main source of big data,
this course also addresses the cloud technologies and services necessary to support big data streaming
and processing. TinyML technology is integrated in the course as well, to enable students to know about
embedded machine learning.
CSC 3331 Introduction to Big Data Environment and Application (3 SCH)
Prerequisite: CSC 3326
3 lecture hours
The course introduces Big Data management and techniques that can be applied to massive datasets in
distributed environments. The course covers the Map-Reduce parallel computing paradigm and Hadoop
distributed file system. The course reviews data storage and preparation for applications, including some
machine learning algorithms used for mining knowledge in datastores, including NoSQL.
CSC 3346 Data Engineering and Visualization (3 SCH)
Prerequisites: CSC 3326
3 lecture hours
```


[6] source: academic_catalog_2024_2025, pages: [239, 240]

```text
and to develop the necessary skills of Modeling, Analysis and Design, including System Architecture and
Technology Stack issues, necessary to this end.
CSC 3326 Database Systems (3 SCH)
Prerequisite: CSC 2306 (or CSC 1402 or BAI 3301) and Junior classification
3 lecture hours
The course covers the design and implementation of Relational databases. While significant focus is
placed on Entity-Relationship and Relational modeling, other models and current trends in database are
introduced. Relational Algebra and SQL are covered, including procedural SQL. A Relational DBMS is
used along with database application development as lab work and class projects. Transactions and
concurrency issues are also addressed.
Al Akhawayn University
www.aui.ma
2024-
2025
240
CSC 3328 Embedded Systems (3 SCH)
Prerequisite: CSC 3351
3 lecture hours
This course surveys the application of computing systems in a range of devices ranging from nomadic
```


[7] source: academic_catalog_2024_2025, pages: [213]

```text
Al Akhawayn University
www.aui.ma
2024-
2025
213
Basic Sciences (16 SCH)
Area 3: General Engineering (50 SCH)
Required Core Courses:
Area 4: Renewable Energy Major (18 SCH)
Required Major Courses (9 SCH)
Course Code Course Name
CHE 1401 Chemistry I
CHE 1402 Chemistry II
PHY 1401 Physics I
PHY 1402 Physics II
Course Code Course Name
RES 3311 Introduction to Physics of Energy
RES 4323 Power Distribution Systems and Smart Grids
RES 4325 Introduction to Renewable Energy Technologies and Sustainability
Course Code Course Name
CSC 1402 Computer Programming for Engineers
CSC 3308 Data Analysis (with Python)
EGR 2201 Introduction to Engineering and Design
EGR 2210 Computer Aided Engineering
EGR 2301 Statics
EGR 2302 Engineering Economics
EGR 2311 Dynamics
EGR 2402 Electric Circuits
EGR 3401 Fluid Mechanics
EGR 3302 Thermodynamics
EGR 3304 Materials Science
EGR 3305 Systems, Signals, and Control
EGR 3306 Engineering Instrumentation and Mechatronics
EGR 3331 Digital Design
EGR 4300 Internship
EGR 4402 Capstone Design
```


[8] source: academic_catalog_2024_2025, pages: [240, 241]

```text
to design and create data visualizations based on data available and business objectives. This includes
data modeling, basic data processing, such as aggregation and filtering, mapping data attributes to
graphical attributes, and strategic visual encoding based on known properties of visual perception as well
as the task(s) at hand. Students will learn how to use Open Source data visualization tools, such as D3.js.
`
Al Akhawayn University
www.aui.ma
2024-
2025
241
CSC 3347 Machine Learning and Data Mining (3 SCH)
Prerequisites: CSC 3308 or CSC 3309
3 lecture hours
The course covers the most popular machine learning algorithms used for discovering meaningful
patterns and knowledge from large amounts of data, including Artificial Neural Networks, Decision Trees,
Association Rule Mining, Clustering algorithms, K-Nearest Neighbor approaches, etc.
CSC 3348 Natural Language Processing and Text Mining (3 SCH)
Prerequisites: CSC 3308 or CSC 3309
3 lecture hours
```


[9] source: academic_catalog_2024_2025, pages: [424, 425]

```text
Geneva, Switzerland.
Al Akhawayn University
www.aui.ma
2024-
2025
425
El Bouchikhi, Yassine, PhD in Management Science, Paris Dauphine University – PSL Research,
France.
El Garah, Ouafaa, Ph.D. in Management Information Systems, University of Central Florida, Orlando,
Florida, USA.
Fakhar, Ahlam, Ph.D. in Economics, Claremont Graduate University, Claremont, California, USA.
Gamar, Alae, Master of Business Administration, Al Akhawayn University in Ifrane, Morocco.
Hamidi Alaoui, Abdelhamid, Ph.D. in Mathematics, University of Oklahoma, Norman, Oklahoma, USA.
Hammoud, Rhizlane, Master of Business Administration, Michigan State University, East Lansing,
Michigan, USA.
Hassi, Abderrahman, Doctorate in Relations Industrielles, Laval University, Quebec, Canada.
Ikram, Muhammed , Ph.D. in Management, Nanjing University of Aeronautics and Astronautics,
Nanjing, China.
Jabbouri, Imad, Ph.D. in Finance, ESC Rennes School of Business, Rennes, France.
Konou, Comlanvi Martin, Ph.D. in Economics,
```


[10] source: academic_catalog_2024_2025, pages: [373, 374]

```text
2 lecture hours
This course emphasizes the integration of cost and strategic analysis. Participants enhance the ability to
critically analyze and interpret the use of cost data for planning and control. The module includes activity-
based costing, target costing, value chain analysis, performance measurement matrices (e.g., balanced
scorecard), strategic positioning, incentives management, and performance management.
Al Akhawayn University
www.aui.ma
2024-
2025
374
Computer Science (CSC)
CSC 5199 Advanced Database Systems
1 lecture hour
Used by students who must be registered in order to have a degree conferred.
CSC 5301 Advanced Database Systems and Data Warehousing (3 SCH)
Prerequisite: CSC 3326
3 lecture hours
This course covers advanced issues in database design, including distributed and object-oriented
databases, database optimization, etc. Significant focus will be placed on data warehousing, including
case study analysis and project design.
CSC 5333 Master’s Thesis (3 SCH)
```


---

## 7. intl_scholarships_en#1

**Your label:** supported

**Judge:** supported -> final unsupported (quote check: FAILED -- quote not found in these passages)

**Claim** (uncited, checked against all passages):

> Al Akhawayn University offers a few merit‑based scholarship programmes that international students can apply to.

**Judge's quote:** 'AUI Scholarships for New Students... AUI Scholarships for Continuing Students... Alumni’s child discount is available to international students'

**Judge's reason:** The passages explicitly mention scholarships available to international students, including new and continuing students, and the alumni-child discount.

**Question:** What scholarships are available for international students?

<details><summary>Full answer</summary>

```text
Al Akhawayn University offers a few merit‑based scholarship programmes that international students can apply to.  The main options are:

| Scholarship type | Who can apply | Key eligibility points | Application deadline | Source |
|-------------------|---------------|------------------------|----------------------|--------|
| **AUI Scholarships for New Students** | Newly admitted undergraduate students (including international entrants) | • Minimum “mention Bien” (14/20) on a Moroccan or French baccalaureate, or equivalent <br>• SGPA ≥ 3.50/4.00 for an American baccalaureate, or <br>• 90 % or better on a Middle‑Eastern baccalaureate, or <br>• 8/10 (16/20) or better on a Spanish baccalaureate, or <br>• 26/30 or better on an Italian baccalaureate <br>• Superior General Admission Test (GAT) score <br>• Positive rating at the scholarship interview <br>• Required essay | Most awards are made only for the Fall session (application due before the Fall intake) | [2] |
| **AUI Scholarships for Continuing Students** | Undergraduate and graduate students already enrolled (including international students) | • Merit‑based award for undergraduates (≥ 3.00/4.00 GPA) and for graduates (≥ 3.50/4.00 GPA) <br>• Must submit a Graduate Scholarship Form (for graduate programmes) | • 31 May for the Fall semester <br>• 31 October for the Spring semester | [4] |
| **Alumni‑Child Discount** | Children of AUI alumni (international students included) | • 10 000 MAD discount (or 5 000 MAD for sibling discount) <br>• Available to international students as well | No separate application – automatically considered if the parent is an alumnus and the student meets the criteria | [5] |

**Important notes**

* All AUI scholarships are **merit‑based**; they are awarded on academic achievement and not on financial need.  
* Scholarship recipients are required to maintain the stated GPA thresholds (≥ 3.00/4.00 for undergraduates, ≥ 3.50/4.00 for graduates) to keep the award.  
* Students who receive a full external scholarship or other financial aid cannot combine it with an AUI scholarship or discount.  
* International students should confirm their eligibility and any specific requirements with the Office of Financial Aid or the Office of International Programs.

For the most up‑to‑date application forms, deadlines, and any additional scholarship opportunities that may arise, please contact the Financial Aid Office or consult the AUI academic catalog.
```

</details>

**Passages:**

[1] source: prestigious_scholarships, pages: []

```text
Prestigious scholarships
Prestigious scholarships
Home
Tuition and Fees
AUIers with top scolarships
Shining Globally Through Prestigious Scholarships
Al Akhawayn University takes immense pride in the remarkable achievements of its students, many of whom have earned prestigious scholarships at both national and international levels. These scholarships recognize the academic excellence, leadership, and dedication of AUI students, offering them opportunities to study at globally renowned institutions and participate in transformative experiences. From the university’s own Excellence Awards for high-achieving students to global honors like the McCall MacBain Scholarship at McGill University, AUI students continue to shine on the international stage. These accolades reflect the university's commitment to fostering a culture of excellence, empowering its students to thrive academically and contribute meaningfully to the world.
Our students
A place where inspiration finds you
```


[2] source: academic_catalog_2024_2025, pages: [65, 66]

```text
is3.00/4.00 or higher
Al Akhawayn University
www.aui.ma
2024-
2025
66
AUI Scholarships for New Students
A scholarship is a merit-based offer awarded to newly admitted undergraduate students. A student’s
academic achievement determines his/her eligibility for the scholarship and the amount to be awarded
regardless of his/her financial need. Most awards are made only for the Fall session.
Scholarship Eligibility Criteria
Scholarships are offered to students with excellent academic profiles based on the following:
Undergraduates
• A Moroccan or French baccalaureate or equivalent with a minimum “mention Bien” (14/20)
▫ Or an American baccalaureate with an SGPA of at least 3.50/4.00
▫ Or a Middle Eastern baccalaureate with 90% or better
▫ Or a Spanish baccalaureate of 8/10 (16/20) or better
▫ Or an Italian baccalaureate with at least 26/30.
• A superior achievement in the General Admission Test score (GAT)
• A superior rating at the scholarship interview
• Essay as required in the online scholarship form:
```


[3] source: academic_catalog_2024_2025, pages: [61]

```text
Withdrawal Form” available at the DSA (Dean of Student Affairs) Office. This petition must be
accompanied by adequate documentation and bear all required administrative signatures, mainly
the physician’s confirmation of the student’s health conditions. Such cases with completed and
approved retroactive forms should be reviewed by the scholarship committee to decide on the
student’s financial aid status for the following semester.
• The financial aid renewal policy adopted by Al Akhawayn is also applicable to financial aid students
on exchange at the end of their exchange program semester. Passing grades are determined in the
Transfer Grades Chart available at the Office of the Registrar and communicated by the Office of
International Programs to students when applying to partner universities.
Semester GPA Financial Aid forthefollowing semester
≥ 3.00/4.00 Good standing: grant is maintained
2.50/4.00 – 2.99/4.00 Grant probation: grant is conditionally maintained;
```


[4] source: academic_catalog_2024_2025, pages: [73, 74]

```text
nal Studies and Diplomacy (MAISD), the North African and Middle Eastern Studies (NAMES) or
to the Master of Arts in Islamic Studies (MAIS) programs at the School of Humanities and Social
Sciences.
Candidates can apply for a merit-based scholarship by completing the Graduate Scholarship
Form and submitting it to the Financial Aid Office before the following set deadlines:
• 31 May for the Fall semester
• 31 October for the Spring semester
Conditions for the AUI External Scholarship
All sponsorship beneficiaries have to abide by the AUI regulations in terms of their scholarship
renewal criteria (≥3.00/4.00 or better for undergraduates and ≥3.50/4.00 or better for graduates)
as well as unpaid campus employment that is part of their scholarship package.
Students benefiting from any full external scholarship or financial aid are not eligible to combine
it with any other AUI discount.
Al Akhawayn University
www.aui.ma
2024-
2025
74
AUI Scholarships for Continuing Students
Purpose
```


[5] source: academic_catalog_2024_2025, pages: [64, 65]

```text
semester
≤ 2.49/4.00 Financial aid suspension until SGPA is3.00/4.00 or higher
2.50/4.00 – 2.99/4.00 after
two consecutive semesters
Financial aid suspension until SGPA is 2.00/4.00 or higher
At the end of any semester: SGPA with “W” , “F” , “WP” , or
“WF” in all courses
Financial aid suspension for the following semester until SGPA is
3.00/4.00 or higher
Al Akhawayn University
www.aui.ma
2024-
2025
65
Unlike financial aid, the alumni’s child discount is available to international students. Alumni’s
child beneficiaries are also allowed to reside in a single room. Those on financial aid must be
aware that this offer of 10000 MAD is already included in their financial aid package.
They are not allowed to combine this offer with any other form of discount (like scholarship,
financial aid, sibling discount, or other…). Moreover, this discount is not effective on a retroactive
basis.
Also, scholarship students meeting the alumni’s child criteria are not eligible to benefit from this
```


[6] source: academic_catalog_2024_2025, pages: [5]

```text
REQUIRED DOCUMENTS FOR FINANCIAL AID 50
APPLICATION DEADLINES   52
TYPES OF FINANCIAL AID OFFERED AT AUI 52
AUI Scholarships for New Students  66
AUI Scholarships for Continuing Students  74
STUDENT SUPPORT    75
Center for Learning Excellence (CLE)  75
Student Services    77
Student Life    78
Athletics     81
Student Housing    85
Student Conduct    86
Campus Store    87
Counseling    87
Health Center    88
Dining Services    88
Computer and Email Support   88
ACADEMIC RESOURCES  92
Mohammed VI Library  92
Advising for Freshmen  93
The office of Employability & Entrepreneurship  93
Office of Academic Support and Progress (OASP)  94
Office of International Programs  94
REGISTRATION REGULATIONS  97
Academic Advising  97
Preregistration  97
Regular Registration  97
Late Registration  97
Class Day  97
Semester Credit Hour  97
Prerequisites  98
Academic Calendar  98
Enrollment Certificates  98
Student Transcripts  98
Certificate of Completion  98
Name Change of Current Students  99
Death of a Current Student  99
```


[7] source: academic_catalog_2024_2025, pages: [52]

```text
awarded in the form of a fixed amount that goes exclusively towards tuition to prospective students with
demonstrated financial need and commendable academic records. The amount granted to students
should not exceed the amount paid for tuition.
Grants come in the form of funds (endowments) held by the University or donations (private, semi-
private, or state donations). Donation providers are mainly local communities, companies, banks, board
members, ministries, social charity organizations, international or Moroccan charities, and socio-cultural
associations. Contributions from individual benefactors are included in this group. Special nominal
scholarships are also available. Such information may be obtained from the Financial Aid Office. Newly
admitted financial aid applicants should confirm their admission to AUI by paying a deposit of 25,000
DHS so that their files can be reviewed by the financial aid committee.
```


[8] source: academic_catalog_2024_2025, pages: [58]

```text
It is also available to international students. Sibling beneficiaries are allowed to reside in a single
room. If the 1st sibling is dismissed for whatever reason (academic or disciplinary), the sibling
discount is maintained. However, if the 1st sibling withdraws from AUI for personal reasons the
sibling discount is terminated.
If the first child, whether still enrolled or graduated from AUI, benefits from a full scholarship, an
additional child is not eligible to benefit from this discount. In addition, scholarship students are
not eligible to benefit from this discount unless they are placed on scholarship suspension with
good academic standing. Moreover, this discount is not effective on a retroactive basis. Sibling
discount beneficiaries on financial aid must be aware that their sibling child discount of 5000 MAD
is already included in their financial aid package.
Eligibility for Financial Aid/Grant
```


[9] source: academic_catalog_2024_2025, pages: [94]

```text
to the new academic environment.
• Providing a central point of contact for all academic matters.
• Monitoring student academic progress throughout the semester and over the course of studies
to improve their persistence and degree completion.
• Providing support and ensuring the success of students throughout their academic journey.
• Assisting students with all aspects of academic advising.
Contact: office.academic.support@aui.ma
Office of International Programs
AUI is, by design and mission, an international university. The university’s mission and programs
foster an international perspective and international understanding. To that end, the Office of
International Programs promotes and advances the internationalization of AUI at all levels. Some
of the key functions of the OIP include exchange and study abroad programs, internationalization
at home, strategic partnerships, and related services to members of the AUI community.
Exchange and Study Abroad Programs
```


---

## 8. intl_scholarships_en#4

**Your label:** unsupported

**Judge:** supported -> final supported (quote check: passed)

**Claim** (own, checked against [4]):

> Scholarship type: **AUI Scholarships for Continuing Students**; Who can apply: Undergraduate and graduate students already enrolled (including international students); Key eligibility points: • Merit‑based award for undergraduates (≥ 3.00/4.00 GPA) and for graduates (≥ 3.50/4.00 GPA)  • Must submit a Graduate Scholarship Form (for graduate programmes); Application deadline: • 31 May for the Fall semester  • 31 October for the Spring semester; Source: [4]

**Judge's quote:** 'Candidates can apply for a merit-based scholarship by completing the Graduate Scholarship Form and submitting it to the Financial Aid Office before the following set deadlines: • 31 May for the Fall semester • 31 October for the Spring semester... Conditions for the AUI External Scholarship... (≥3.00/4.00 or better for undergraduates and ≥3.50/4.00 or better for graduates)'

**Judge's reason:** All details in the claim match the passage [4] verbatim or are directly paraphrased.

**Question:** What scholarships are available for international students?

<details><summary>Full answer</summary>

```text
Al Akhawayn University offers a few merit‑based scholarship programmes that international students can apply to.  The main options are:

| Scholarship type | Who can apply | Key eligibility points | Application deadline | Source |
|-------------------|---------------|------------------------|----------------------|--------|
| **AUI Scholarships for New Students** | Newly admitted undergraduate students (including international entrants) | • Minimum “mention Bien” (14/20) on a Moroccan or French baccalaureate, or equivalent <br>• SGPA ≥ 3.50/4.00 for an American baccalaureate, or <br>• 90 % or better on a Middle‑Eastern baccalaureate, or <br>• 8/10 (16/20) or better on a Spanish baccalaureate, or <br>• 26/30 or better on an Italian baccalaureate <br>• Superior General Admission Test (GAT) score <br>• Positive rating at the scholarship interview <br>• Required essay | Most awards are made only for the Fall session (application due before the Fall intake) | [2] |
| **AUI Scholarships for Continuing Students** | Undergraduate and graduate students already enrolled (including international students) | • Merit‑based award for undergraduates (≥ 3.00/4.00 GPA) and for graduates (≥ 3.50/4.00 GPA) <br>• Must submit a Graduate Scholarship Form (for graduate programmes) | • 31 May for the Fall semester <br>• 31 October for the Spring semester | [4] |
| **Alumni‑Child Discount** | Children of AUI alumni (international students included) | • 10 000 MAD discount (or 5 000 MAD for sibling discount) <br>• Available to international students as well | No separate application – automatically considered if the parent is an alumnus and the student meets the criteria | [5] |

**Important notes**

* All AUI scholarships are **merit‑based**; they are awarded on academic achievement and not on financial need.  
* Scholarship recipients are required to maintain the stated GPA thresholds (≥ 3.00/4.00 for undergraduates, ≥ 3.50/4.00 for graduates) to keep the award.  
* Students who receive a full external scholarship or other financial aid cannot combine it with an AUI scholarship or discount.  
* International students should confirm their eligibility and any specific requirements with the Office of Financial Aid or the Office of International Programs.

For the most up‑to‑date application forms, deadlines, and any additional scholarship opportunities that may arise, please contact the Financial Aid Office or consult the AUI academic catalog.
```

</details>

**Passages:**

[4] source: academic_catalog_2024_2025, pages: [73, 74]

```text
nal Studies and Diplomacy (MAISD), the North African and Middle Eastern Studies (NAMES) or
to the Master of Arts in Islamic Studies (MAIS) programs at the School of Humanities and Social
Sciences.
Candidates can apply for a merit-based scholarship by completing the Graduate Scholarship
Form and submitting it to the Financial Aid Office before the following set deadlines:
• 31 May for the Fall semester
• 31 October for the Spring semester
Conditions for the AUI External Scholarship
All sponsorship beneficiaries have to abide by the AUI regulations in terms of their scholarship
renewal criteria (≥3.00/4.00 or better for undergraduates and ≥3.50/4.00 or better for graduates)
as well as unpaid campus employment that is part of their scholarship package.
Students benefiting from any full external scholarship or financial aid are not eligible to combine
it with any other AUI discount.
Al Akhawayn University
www.aui.ma
2024-
2025
74
AUI Scholarships for Continuing Students
Purpose
```


---

## 9. intl_scholarships_fr#13

**Your label:** supported

**Judge:** supported -> final unsupported (quote check: FAILED -- quote not found in these passages)

**Claim** (uncited, checked against all passages):

> Les bourses de poursuite exigent un suivi régulier de la moyenne et peuvent être suspendues en cas de baisse de performance.

**Judge's quote:** 'renewal criteria (≥3.00/4.00 or better for undergraduates and ≥3.50/4.00 or better for graduates)... Financial aid suspension until SGPA is 3.00/4.00 or higher'

**Judge's reason:** The passages confirm that continuing scholarships require regular GPA monitoring and can be suspended for poor performance.

**Question:** Quelles bourses sont disponibles pour les étudiants internationaux ?

<details><summary>Full answer</summary>

```text
Les étudiants internationaux peuvent bénéficier de plusieurs bourses proposées par l’Université Al Khawayn (AUI). Voici un aperçu des principales options :

| Type de bourse | Destinataires | Conditions principales | Détails supplémentaires |
|----------------|--------------|------------------------|--------------------------|
| **Bourses d’entrée (New‑Student Scholarships)** | Étudiants nouvellement admis en licence (baccalauréat) | • Résultat académique excellent (voir critères ci‑dessous)<br>• Score élevé au General Admission Test (GAT)<br>• Bonnes notes à l’entretien de bourse<br>• Rédaction d’un essai | • Les bourses sont attribuées sur la base de la performance, pas de besoins financiers.<br>• La plupart des allocations sont versées uniquement pour la session d’automne. | [9] |
| **Bourses pour étudiants en poursuite (Continuing‑Student Scholarships)** | Étudiants déjà inscrits (licence ou master) | • Remplir le formulaire de bourse graduate<br>• Soumettre avant les dates limites (31 mai pour l’automne, 31 octobre pour le printemps)<br>• Maintenir une moyenne générale d’au moins 3,00/4,00 (ou 3,50/4,00 pour les diplômés)<br>• Les bourses ne peuvent pas être combinées avec d’autres remises AUI | • La bourse est renouvelée chaque semestre tant que les critères de GPA sont respectés.<br>• Si le GPA chute, la bourse est suspendue jusqu’à ce que la moyenne redevienne satisfaisante. | [10] |
| **Bourses externes prestigieuses** | Étudiants AUI, y compris les internationaux | • Bourses offertes par des institutions partenaires (ex. McCall MacBain Scholarship à McGill, etc.)<br>• Souvent basées sur l’excellence académique et le leadership | • Ces bourses sont indépendantes du financement AUI et ne peuvent pas être combinées avec d’autres aides AUI. | [8] |

### Critères d’éligibilité pour les bourses d’entrée (extrait de [9])

- **Baccalauréat marocain ou français** : mention « Bien » (≥ 14/20)  
- **Baccalauréat américain** : SGPA ≥ 3,50/4,00  
- **Baccalauréat du Moyen‑Orient** : ≥ 90 %  
- **Baccalauréat espagnol** : ≥ 8/10 (≈ 16/20)  
- **Baccalauréat italien** : ≥ 26/30  

### Points à retenir

- Les bourses sont **merit‑based** (basées sur la performance) et non sur le besoin financier.  
- Les étudiants internationaux répondant aux critères ci‑dessus sont éligibles aux mêmes bourses que les étudiants marocains.  
- Les bourses de poursuite exigent un suivi régulier de la moyenne et peuvent être suspendues en cas de baisse de performance.  
- Les bourses externes prestigieuses offrent des opportunités d’études à l’étranger et sont souvent très compétitives.

Si vous souhaitez postuler, consultez le formulaire de bourse et les dates limites sur le site de l’Université ou contactez le **Financial Aid Office** pour obtenir plus d’informations.
```

</details>

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [7, 8, 9]

```text
Center for Business Ethics 423
Center for Teaching and Learning 423
UNIVERSITY FACULTY 424
School of Business Administration 424
School of Science and Engineering 426
School of Humanities and Social Sciences 429
Language Center 434
Disclaimer
The material included in this catalog is based on information available as of Fall 2023 and is subject to change.
Students enrolling in Fall 2023 shall abide by the graduation requirements herein, and students enrolling in Spring
2024 shall abide by the same requirements or any changes or addenda that are published.
Al Akhawayn University
www.aui.ma
2024-
2025
9
Welcome to Al Akhawayn University in Ifrane (AUI)!
I am very happy you are connecting with us, whether
you are a prospective student, a parent, a partner, or
an alumnus. We are more than just an institution of
learning, we are a vibrant community dedicated to
personal growth, discovery, and global
impact.
We are a liberal arts university in Morocco committed
to marrying universal Excellence and Moroccan
```


[2] source: academic_catalog_2024_2025, pages: [42, 43]

```text
any other document.
The student is the sole party responsible vis-à-vis the University with regard to payment matters.
Payments can be made by wire transfers, cash deposit in banks, online credit card payments, or certified
bank checks. These fees are subject to change each academic year at the discretion of the Board of
Trustees.
Registration Fees: 5100 MAD
All registered students must pay registration fees regardless of status. Students who defend their theses,
capstones, or internships before the end of a semester receive a prorated reimbursement  of their
registration fees.
Registration fees cover fixed costs, such as: student health services, student activities, athletics,
swimming pool access, restaurant access, IT services.
Al Akhawayn University
www.aui.ma
2024-
2025
43
Tuition
Semester tuition is calculated based on the total credits taken, except for students enrolled in the
Language Center, who are charged a flat amount.
```


[3] source: academic_catalog_2024_2025, pages: [128, 129]

```text
earned a passing grade toward the ordinary AUI graduation requirements.
Withdrawal Policy
• Students intending to withdraw from the UHP must promptly notify the UHPC by completing the
UHP Withdrawal Form (provided by the UHP Office).
• Students who fail to enroll in any Honors Courses for two consecutive semesters without official
notification to the UHPC will be automatically withdrawn from the UHP .
Al Akhawayn University
www.aui.ma
2024-
2025
129
BACHELOR’S DEGREE PROGRAMS
• Bachelor of Business Administration (BBA)
• Bachelor of Arts in International Studies (BAIS)
• Bachelor of Science in Human Resource Development (BSHRD)
• Bachelor of Arts in Communication Studies (BACS)
• Bachelor of Science in Environmental Studies and Sustainability (BSESS)
• Bachelor of Science in Territorial Planning and Management (BSTPM)
• Bachelor of Science in Psychology (BSP)
• Bachelor of Science in Computer Science (BSCSC)
• Bachelor of Science in Big Data Analytics (BSBDA)
```


[4] source: academic_catalog_2024_2025, pages: [143, 144]

```text
ECO 2301 Microeconomics
ECO 2302 Macroeconomics
FIN 3301 Principles of Finance
GBU 2301 Business Statistics
GBU 3302 Business Law and Ethics
GBU 3203 Enterprises, Markets, and the Moroccan Economy
GBU 3311 Quantitative Methods in Business
GBU 4101 Transitioning To The Business World
INT 4001 Internship Field Work
INT 4301 Internship
MGT 3301 Principles of Management
MGT 3302 Entrepreneurship
MGT 4301 Capstone Course: Business Policy and Corporate Strategy
MGT 4303 Operations Management
MIS 3301 Management Information Systems
MKT 3301 Principles of Marketing
Al Akhawayn University
www.aui.ma
2024-
2025
144
Course Code Course Name
FIN 3302 Money and Banking
FIN 3303 Corporate Financial Management
FIN 3305 Introduction to Islamic Banking and Finance
FIN 3306 Corporate Governance
FIN 3307 Financial Reporting and Analysis
FIN 3399 Special Topics in Finance
FIN 4304 International Finance
FIN 4305 Financial Intermediation
FIN 4306 Financial Investments and Securities Analysis
```


[5] source: academic_catalog_2024_2025, pages: [24, 25, 26, 27]

```text
Touhami, Yassir
Chief Financial Officer
Ben El Jarbouh, Abderrahim
Director, Business Services
Ali, El Awad
Executive Director for Support & Administration
Nouamani, Said
Director, Procurement and Infrastructure Development`
2024-
2025
25
Harroud, Hamid
Director, Information Technology Services
Jadid, Mohammed
Director, Grounds and Maintenance
Bouflous, Mohammed
Director, Security and Safety Department
Other Senior Administrators
Office for Institutional Research and Effectiveness
Belfekih, Moulay Cherif
Executive Director
Office of Internal Audit
Mechiche, Souhail
Junior Auditor, Internal Audit and Management Control
Department of Development and Communication
Dalil, Hamza
Chief Marketing Officer in charge of Development and Communication,
Outreach, and Admissions
Office of Human Capital
Hazzaz, Safia
Director of Human Capital
Al Akhawayn University
www.aui.ma
2024-
2025
26
2024-
2025
27
ADMISSIONS
Al Akhawayn University encourages all academically qualified senior high school students
```


[6] source: academic_catalog_2024_2025, pages: [52]

```text
DHS so that their files can be reviewed by the financial aid committee.
2. AUI-Approved Bank Loans “Avenir Plus” or State Guaranteed Loan with CCG (Caisse Cen-
trale de Garantie)
Al Akhawayn University has convened agreements with a national bank for a loan program that will serve
the interests of students and at the same time enable them to contribute substantially toward financing
their own studies. Student loans are offered for the purpose of meeting the costs of studies at AUI.
They are available to all interested students for any semester while the bank bases the final decision on
adequate supporting documentation.
-  Loan Terms and Amounts
• Undergraduate Students
The loan program will provide qualified students with long-term loans payable over an extended period
with %0 annual interest rate, as the interest is supported by AUI. Students may borrow up to
50,000 MAD per year. Repayment begins 12 months following the date of the last amount released by the
```


[7] source: academic_catalog_2024_2025, pages: [261, 262]

```text
nation and the relationship of commercial banking with the supply and demand for money. This course
also analyses monetary concepts, central banking functions, and techniques of monetary stabilization.
FIN 3303 Corporate Financial Management (3 SCH)
Prerequisite: FIN 3301
3 lecture hours
This course continues the study of financial decision-making in corporations. The main
topics covered are advanced ratios analysis, capital budgeting, capital structure, dividend policy, and
an introduction to portfolio management. The course also provides an in-depth analysis of financial
problems with the organization, operation, merger, and dissolution of corporations.
Al Akhawayn University
www.aui.ma
2024-
2025
262
FIN 3305 Introduction to Islamic Banking and Finance (3 SCH)
Prerequisite: FIN 3301
3 lecture hours
This course discusses the basic differences between Islamic banks and conventional banks, financial
instruments of Islamic banks, profit/loss sharing, Takaful, capital markets, and unique risks faced by
```


[8] source: prestigious_scholarships, pages: []

```text
Prestigious scholarships
Prestigious scholarships
Home
Tuition and Fees
AUIers with top scolarships
Shining Globally Through Prestigious Scholarships
Al Akhawayn University takes immense pride in the remarkable achievements of its students, many of whom have earned prestigious scholarships at both national and international levels. These scholarships recognize the academic excellence, leadership, and dedication of AUI students, offering them opportunities to study at globally renowned institutions and participate in transformative experiences. From the university’s own Excellence Awards for high-achieving students to global honors like the McCall MacBain Scholarship at McGill University, AUI students continue to shine on the international stage. These accolades reflect the university's commitment to fostering a culture of excellence, empowering its students to thrive academically and contribute meaningfully to the world.
Our students
A place where inspiration finds you
```


[9] source: academic_catalog_2024_2025, pages: [65, 66]

```text
is3.00/4.00 or higher
Al Akhawayn University
www.aui.ma
2024-
2025
66
AUI Scholarships for New Students
A scholarship is a merit-based offer awarded to newly admitted undergraduate students. A student’s
academic achievement determines his/her eligibility for the scholarship and the amount to be awarded
regardless of his/her financial need. Most awards are made only for the Fall session.
Scholarship Eligibility Criteria
Scholarships are offered to students with excellent academic profiles based on the following:
Undergraduates
• A Moroccan or French baccalaureate or equivalent with a minimum “mention Bien” (14/20)
▫ Or an American baccalaureate with an SGPA of at least 3.50/4.00
▫ Or a Middle Eastern baccalaureate with 90% or better
▫ Or a Spanish baccalaureate of 8/10 (16/20) or better
▫ Or an Italian baccalaureate with at least 26/30.
• A superior achievement in the General Admission Test score (GAT)
• A superior rating at the scholarship interview
• Essay as required in the online scholarship form:
```


[10] source: academic_catalog_2024_2025, pages: [73, 74]

```text
nal Studies and Diplomacy (MAISD), the North African and Middle Eastern Studies (NAMES) or
to the Master of Arts in Islamic Studies (MAIS) programs at the School of Humanities and Social
Sciences.
Candidates can apply for a merit-based scholarship by completing the Graduate Scholarship
Form and submitting it to the Financial Aid Office before the following set deadlines:
• 31 May for the Fall semester
• 31 October for the Spring semester
Conditions for the AUI External Scholarship
All sponsorship beneficiaries have to abide by the AUI regulations in terms of their scholarship
renewal criteria (≥3.00/4.00 or better for undergraduates and ≥3.50/4.00 or better for graduates)
as well as unpaid campus employment that is part of their scholarship package.
Students benefiting from any full external scholarship or financial aid are not eligible to combine
it with any other AUI discount.
Al Akhawayn University
www.aui.ma
2024-
2025
74
AUI Scholarships for Continuing Students
Purpose
```


[11] source: academic_catalog_2024_2025, pages: [61]

```text
Withdrawal Form” available at the DSA (Dean of Student Affairs) Office. This petition must be
accompanied by adequate documentation and bear all required administrative signatures, mainly
the physician’s confirmation of the student’s health conditions. Such cases with completed and
approved retroactive forms should be reviewed by the scholarship committee to decide on the
student’s financial aid status for the following semester.
• The financial aid renewal policy adopted by Al Akhawayn is also applicable to financial aid students
on exchange at the end of their exchange program semester. Passing grades are determined in the
Transfer Grades Chart available at the Office of the Registrar and communicated by the Office of
International Programs to students when applying to partner universities.
Semester GPA Financial Aid forthefollowing semester
≥ 3.00/4.00 Good standing: grant is maintained
2.50/4.00 – 2.99/4.00 Grant probation: grant is conditionally maintained;
```


[12] source: academic_catalog_2024_2025, pages: [64, 65]

```text
semester
≤ 2.49/4.00 Financial aid suspension until SGPA is3.00/4.00 or higher
2.50/4.00 – 2.99/4.00 after
two consecutive semesters
Financial aid suspension until SGPA is 2.00/4.00 or higher
At the end of any semester: SGPA with “W” , “F” , “WP” , or
“WF” in all courses
Financial aid suspension for the following semester until SGPA is
3.00/4.00 or higher
Al Akhawayn University
www.aui.ma
2024-
2025
65
Unlike financial aid, the alumni’s child discount is available to international students. Alumni’s
child beneficiaries are also allowed to reside in a single room. Those on financial aid must be
aware that this offer of 10000 MAD is already included in their financial aid package.
They are not allowed to combine this offer with any other form of discount (like scholarship,
financial aid, sibling discount, or other…). Moreover, this discount is not effective on a retroactive
basis.
Also, scholarship students meeting the alumni’s child criteria are not eligible to benefit from this
```


---

## 10. mth1305_en#2

**Your label:** supported

**Judge:** supported -> final unsupported (quote check: FAILED -- quote not found in these passages)

**Claim** (own, checked against [2], [3]):

> It is listed in the course catalog as a 3‑credit course and is required for students in the SSAH Business Administration minor (and counts toward the general‑education component of their program) [2][3].

**Judge's quote:** 'MTH 1305 “Mathematics for Business”... SSAH students minoring in Business Administration must take MTH 1305 as part of their Gen Ed requirements... [2] lists it as a 3-credit course.'

**Judge's reason:** The passage confirms MTH 1305 is a 3-credit course and is required for SSAH Business Administration minors as part of their general-education component.

**Question:** What is MTH 1305?

<details><summary>Full answer</summary>

```text
MTH 1305 is a general‑education mathematics course titled **“Mathematics for Business.”**  It is listed in the course catalog as a 3‑credit course and is required for students in the SSAH Business Administration minor (and counts toward the general‑education component of their program) [2][3].
```

</details>

**Passages:**

[2] source: academic_catalog_2024_2025, pages: [155]

```text
ART 1304 “Drama and Theater”
ART 1305 “Art Appreciation and Creation”
ART 1399 “Special Topics in Art”
ART 3399 “Special Topics in Cultural Production”
ENG 2320 “Creative Writing” 5COM 2427 “Art and
Design Production”   HUM 2301 “Islamic Art &
Architecture”
LIT 3370 “Aesthetics”
3
6 Mathematics MTH 1388 “Introductory Mathematical Thinking”
MTH 1305 “Mathematics for Business”
MTH 1303 “Calculus I: Differential
and Integral Calculus”
3
7Physical Sciences CHE 1400 “Chemistry and Environment”
BIO 1400 “Environmental Biology” PHY 1400
“Conceptual Physics”
4
8Social Sciences SOC 1301 “Principles of Sociology” SSC 1310 “Intro.
to Anthropology” PSY 1301 “Intro. to Psychology” GEO
1301 “Intro. to Geography”
3
9Civic Engagement XXX ****SL or *SLP 1101 or *CIP 1
1FAS 0210 is a non-degree credit-bearing course, and it is a graduation requirement. It counts for 2 non-
degree credits; i.e., they do not count towards the degree. However, this course can be waived upon a
successful test-out.
```


[3] source: academic_catalog_2024_2025, pages: [156]

```text
take French in their first semester of study at AUI.
4 International Studies majors must take PSC 2301 as part of the Major Core. Only HIS 1301, HIS 2301,
HUM 1310, or HUM 2302 can be taken as part of Gen Ed.
5 COM2427 is open only to students NOT minoring in Communication Studies.
6 SSAH students minoring in Business Administration must take MTH 1305 as part of their Gen Ed
requirements. If they take MTH 1388, its credits will not apply toward their degree requirements, whether
for General Education or elective credit.
7Students majoring in ESS must take “BIO 1401 Principles of Biology” as part of the Major Core. Only a
CHE and PHY course can be taken to fulfill the Physical Sciences component of Gen Ed.
8Students majoring in ESS, IS, or TPM must take “GEO 1301 Introduction to Geography” as part of the
Major Core. Only PSY 1301, SOC 1301, or SSC 1310 can be taken to fulfill the Social Sciences component
```


---

## 11. scholarship_conditions_en#10

**Your label:** supported

**Judge:** supported -> final unsupported (quote check: FAILED -- quote not found in these passages)

**Claim** (uncited, checked against all passages):

> If any of these conditions are not met, the scholarship may be reduced, put on probation, or suspended, and the student may need to re‑apply or seek a new award.

**Judge's quote:** 'Scholarship holders who do not meet the renewal criteria will face reduction, suspension, or termination of the award... If the student fails to return to the required standing, reduction or suspension of the scholarship will apply.'

**Judge's reason:** The claim is supported by the general conditions described in the passages [1], [2], and [3].

**Question:** What are the conditions for keeping an Al Akhawayn scholarship?

<details><summary>Full answer</summary>

```text
**Conditions for keeping an Al Akhawayn scholarship**

| Type of scholarship | Key conditions for continued eligibility |
|---------------------|------------------------------------------|
| **All scholarships (under‑graduate & graduate)** | • Scholarships are granted for a specific program and **cannot be transferred** to another program outside the school in which the recipient was initially accepted. <br>• Newly admitted scholarship recipients may change their chosen program **before the first day of classes**. <br>• Students must **confirm acceptance** of the award and its renewal policy by paying any required deposit before the deadline. <br>• Scholarship holders who do not meet the renewal criteria will face **reduction, suspension, or termination** of the award. [1][2] |
| **Graduate (Master’s) scholarships** | • Maximum of **four enrolling semesters** (including one semester at the Language Center). <br>• Must maintain a **Semester Grade Point Average (SGPA) of at least 3.5**. <br>• If SGPA falls between **3.00 and 3.49**, the student is placed on **scholarship probation**; failure to return to the required standing results in reduction or suspension. <br>• If a student receives **W, WP, or WF in all courses** at the end of a semester, they are **automatically suspended** for the following semester. <br>• Graduate scholarship recipients must provide services to the university by holding **unpaid part‑time jobs** (10 hours/week, 160 hours per semester) as assigned by the Financial Aid Office. [3][1] |
| **Under‑graduate scholarships** | • Scholarships are renewable for the **number of semesters specified** in the program (typically 8 for under‑graduates, 4 for graduates). <br>• Students must maintain an **overall GPA** that meets the program’s minimum (often 3.0 or higher). <br>• Summer‑session GPA is **not counted** for probation, suspension, or reinstatement purposes. <br>• Failure to maintain the required GPA can trigger **probation, suspension, or loss** of the scholarship. [5] |

**Summary**

To keep an Al Akhawayn scholarship, a student must:

1. **Accept the award** and pay any required deposit by the set deadline.  
2. **Maintain the required academic performance** (SGPA ≥ 3.5 for graduate students, GPA ≥ 3.0 for under‑graduates).  
3. **Avoid academic probation or suspension** by staying above the minimum GPA and not receiving all‑withdrawal grades.  
4. **Fulfill service obligations** (for graduate scholars: unpaid part‑time work).  
5. **Respect the non‑transferability** rule and adhere to program‑specific renewal limits (up to four semesters for graduate scholarships).  

If any of these conditions are not met, the scholarship may be reduced, put on probation, or suspended, and the student may need to re‑apply or seek a new award.
```

</details>

**Passages:**

[1] source: graduate_scholarships, pages: []

```text
Scholarships
Scholarships
Graduate Admissions
Lorem Ipsum
A place where inspiration finds you
Scholarship Types Offered based on 12 credits per semester
Scholarship Conditions
Al Akhawayn scholarships are predicated on the following conditions:
Scholarships are granted for specific programs and are not transferable to other programs outside the school to which the scholarship recipient was initially accepted. New admitted candidates enrolled with a scholarship in their first semester at AUI are allowed to change their chosen program before the first day of classes.
Graduate scholarship students benefiting from tuition waiver or more must provide services to Al Akhawayn by holding unpaid part-time jobs as assigned by the Financial Aid Office in different departments or schools at Al Akhawayn. They are required to work 10 hours per week (160 hours per semester) as part of their scholarship package.
```


[2] source: academic_catalog_2024_2025, pages: [66, 67]

```text
• A combination of these elements is used to rank undergraduate scholarship applicants and determine
the type of scholarship they will be awarded, students offered a scholarship should confirm their ac-
ceptance of the award and of its renewal policy by paying a scholarship deposit before the set deadline
stated on the scholarship decision message.
N.B.: High School Diploma must be recently obtained. However, the scholarship offer may also be
extended to one previous Bac year (the scholarship is not limited to first-year students).
Al Akhawayn University
www.aui.ma
2024-
2025
67
Newly admitted scholarship applicants should confirm their admission to AUI by paying any deposit re-
quired by the Admissions or the Financial Aid Office so that their files can be reviewed by the scholarship
committee.
Graduates
• Good post-baccalaureate academic results and recommendation of the school’s graduate com-
mittee with a distinction of at least “Assez Bien” in the “Licence, ” an equivalent for the French sys-
```


[3] source: graduate_scholarships, pages: []

```text
Scholarship Renewal Policy for Graduate Students (Master’s Candidates)
Scholarship beneficiaries are eligible for an Al Akhawayn scholarship for a maximum of four enrolling semesters including one semester at the Language Center. The scholarship renewability depends on demonstrating excellence and successful progress in the student's studies as evidenced by maintaining a Semester Grade Point Average (SGPA) of at least 3.5. If the SGPA falls between 3.00 and 3.49, the student will be placed on scholarship probation. If the student fails to return to the required standing, reduction or suspension of the scholarship will apply. If the student obtains "W" or "WP" or "WF" in all courses at the end of any semester, s/he will be automatically placed on scholarship suspension for the following semester as described in the table below:
```


[4] source: graduate_scholarships, pages: []

```text
NOTE: Admitted graduate students who do not qualify for a scholarship for their first semester at Al Akhawayn cannot be offered the opportunity to apply for it during the subsequent semesters.
Scholarship Eligibility Criteria for Graduate Students (Master’s Candidates)
Good post-Baccalaureate academic records with a distinction for the French system or a CGPA of 3.50/4.00 or better for the American system,
Superior rating at the Admission & Scholarship Interview.
A combination of these elements is used to rank scholarship applicants and determine the type of scholarship they will be awarded. Students offered a scholarship should confirm their acceptance of the award and of its renewal policy by paying a non-refundable advance of 10,000 MAD within the set deadline.
```


[5] source: academic_catalog_2024_2025, pages: [69, 70]

```text
semesters for undergraduates and 4 semesters for graduates. Students should be aware that the sum-
mer session GPA would not be taken into account for probation, suspension, or reinstatement.
Al Akhawayn University
www.aui.ma
2024-
2025
70
Combined Programs for Students with Scholarships
After completing the number of credits specified by their school graduate committee, scholarship holders
have the right to combine bachelor’s and master’s degrees, but they must apply for a new scholarship,
which may be granted based upon their CGPA, dean’s recommendation, and on their involvement and
respect for their commitments. If they are granted the scholarship, this scholarship will go towards the
tuition of the graduate course(s) only. This scholarship for the combined program covers three semesters
only with the possibility to apply for an extension and their scholarship type should not exceed the tuition
```


---

## 12. transfer_credits_fr#5

**Your label:** supported

**Judge:** no_claim -> final no_claim (quote check: n/a (not supported))

**Claim** (uncited, checked against all passages):

> Il est conseillé de vérifier votre situation particulière auprès du service d’inscription ou d’un conseiller académique.

**Judge's quote:** (none)

**Judge's reason:** The claim is advice and does not state a checkable fact.

**Question:** Combien de crédits puis-je transférer à l'AUI depuis une autre université ?

<details><summary>Full answer</summary>

```text
Vous pouvez transférer :

- **Pour les programmes de premier cycle (licence)** : jusqu’à **68 crédits semestriels** maximum [1].
- **Pour les programmes de cycle supérieur (master, doctorat)** : jusqu’à **12 crédits semestriels** maximum [3].

Ces limites s’appliquent aux cours transférés qui ont obtenu les notes requises (A, B ou C + / − pour les licences, et A ou B + / − pour les cycles supérieurs). Il est conseillé de vérifier votre situation particulière auprès du service d’inscription ou d’un conseiller académique.
```

</details>

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [31]

```text
programs or B for graduate programs is subsequently earned by the admission candidate and AUI receives
an official record of the final grade in the course.
Minimum Grades for Transferable Courses
Undergraduate courses that are transferable to AUI must be completed with grades A, B, or C (pluses
and minuses inclusive) or Pass. Graduate courses that are transferable to AUI must be completed with
the grade of A or B (pluses and minuses inclusive). However, other grades may only be transferred if they
meet the university grading system criteria.
AUI evaluates grades based on the mapping done for each institution. The transfer table is available in the
Office of Enrollment. Courses with the grades of Incomplete (I), In Progress (IP), and Withdrawn (W) at
the time of the credit evaluation are nontransferable.
Transfer Credit Maximums
For undergraduate programs, a maximum of 68 semester credits are transferable to AUI.
```


[2] source: academic_catalog_2024_2025, pages: [31, 32]

```text
Transfer Credit Maximums
For undergraduate programs, a maximum of 68 semester credits are transferable to AUI.
Applicants for the programs in the School of Science and Engineering who have attended «classes
préparatoires» may request credit for courses as transfer students. Each application will be considered
individually. Appropriate initial courses at AUI may be based on placement examinations, portfolio
analyses, interviews, and/or other assessments.
Visiting (Non-Degree Seeking) Students
Students in good standing at another college or university may study at AUI with visiting, non-degree
seeking status during the summer or semester. Visiting applicants wishing to convert to regular, degree-
seeking status after one or more semesters at AUI will be required to complete all the General Education
Al Akhawayn University
www.aui.ma
2024-
2025
32
requirements pertaining to their academic programs. Former AUI students do not automatically qualify
for visiting or non-degree status.
```


[3] source: academic_catalog_2024_2025, pages: [38]

```text
www.aui.ma
2024-
2025
38
Transfer Graduate Students
To be considered for admission, graduate transfer students must have a minimum grade point average
of 3.00 on a 4.00 grading scale and be in good standing with their home institution. A maximum of 12
semester credits are transferable toward the degree requirements of an AUI graduate program. Courses
in which the student has achieved a grade of C or lower will not be considered for credit transfer.
Visiting Graduate Students
Students in good standing at another college or university may be considered for regular admission with
visiting status during the summer, fall, or spring semesters. Former AUI students do not automatically
qualify for visiting or non-degree status. Visiting graduate students must enroll for a minimum of 9 credits
and a maximum of 12 credits (plus corresponding lab sessions, if applicable) in the fall and spring. In the
summer session, they must enroll for a total of 6 credits.
Standardized Tests
```


[4] source: academic_catalog_2024_2025, pages: [95, 96, 97]

```text
www.aui.ma
2024-
2025
95
Transfer of Credits
For all study abroad programs, the credits that a student obtains at the host university can be
transferred to equivalent courses at AUI, provided that the student enrolls in courses for which
approval from the appropriate AUI school had been given. Programs have different criteria, and
students are encouraged to read the announcements and plan carefully for their international
study experience.
In addition to full-term exchange or study abroad programs, AUI also organizes shorter-term
faculty-led international trips for AUI academic credit. Finally, AUI also organizes non-credit
international trips, particularly through student activities. All these modes of international
experiences contribute to AUI’s international profile and opportunities.
Al Akhawayn University
www.aui.ma
2024-
2025
96
Al Akhawayn University
www.aui.ma
2024-
2025
97
REGISTRATION REGULATIONS
A student is officially enrolled and eligible to attend classes upon registering for courses and paying
```


[5] source: academic_catalog_2024_2025, pages: [94, 95]

```text
at home, strategic partnerships, and related services to members of the AUI community.
Exchange and Study Abroad Programs
Studying abroad is a key part of most AUI students’ experience, and there are several ways to
engage with these opportunities. Among the study abroad programs available to students,
exchange programs are the most popular and are designed primarily for undergraduate students
to exchange places with students from other institutions with which the university has signed
agreements stipulating student payment requirements to the home and host institutions. The
exchange is generally for one semester, although there are exceptions. Study abroad experiences
generally have a limit of one calendar year, i.e., two full semesters and a summer session.
Al Akhawayn University
www.aui.ma
2024-
2025
95
Transfer of Credits
For all study abroad programs, the credits that a student obtains at the host university can be
```


---

## 13. w_grade_en#1

**Your label:** supported

**Judge:** unsupported -> final unsupported (quote check: n/a (not supported))

**Claim** (uncited, checked against all passages):

> A **“W” grade** indicates that you have withdrawn from the course before the official drop‑add deadline.

**Judge's quote:** (none)

**Judge's reason:** The passage states that a W grade is received when dropping a course by the 40th class day, but it does not specify that the withdrawal must occur *before the official drop-add deadline*.

**Question:** What does a W grade mean, and until when can I drop a course and still get a W?

<details><summary>Full answer</summary>

```text
A **“W” grade** indicates that you have withdrawn from the course before the official drop‑add deadline. It is recorded on your transcript but **does not affect your GPA** or credit count.

You can receive a W only if you drop the class **no later than the 40th class day of a regular semester** (or up to 18 class days in a summer session). After that deadline the instructor will assign either a **WP** (withdrawal with passing performance) or **WF** (withdrawal with failing performance) based on your work up to the time of withdrawal.  

The academic calendar provides the exact dates for each semester. For example, in the 2024‑2025 calendar the last day to drop a course with a W is **October 29** for the fall semester, after which only WP or WF grades can be assigned.  

So, to get a W you must drop the course by the 40th class day (or the specified calendar date such as Oct 29) and before any instructor‑based grading takes place.
```

</details>

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [103, 104]

```text
not reflected on the academic record. Failure to attend a class without dropping will result in a
failing grade of WF on the academic record.
Although no refund will be given up to the 40th class day of the regular semester and up to 18 class
days of the summer session (refer to academic calendar for published dates), students may drop
one or more courses and receive a grade of W. This becomes part of the student’s academic record.
After that period, instructors have the responsibility of determining the grade based on classroom
performance up to the time of the student’s request to withdraw from the course. Faculty must
assign either a grade of WP (at the time of withdrawing), or WF (if failing). This process is complete
only when the form bearing all required signatures is returned to the Registrar’s Office.
Al Akhawayn University
www.aui.ma
2024-
2025
104
Students may withdraw from all classes after the last date to drop/add courses with permission
```


[2] source: academic_catalog_2024_2025, pages: [104]

```text
Al Akhawayn University
www.aui.ma
2024-
2025
104
Students may withdraw from all classes after the last date to drop/add courses with permission
from their dean or the Language Center director (if they are enrolled in the Language Center
modules only). For refund dates, see the Refund Policy in the Tuition, Fees, and Deposits section
of the catalog.
Withdrawing from the University
Withdrawing from the University should not be confused with dropping one or more courses while
remaining enrolled in others. Students desiring to drop every course in which they are enrolled
are considered to be withdrawing. Students who officially withdraw from the University prior to
mid-semester will have the grade of W recorded on the transcript. Students wishing to withdraw
after mid-semester may do so with the permission of their dean and will receive the grade of WP
(if passing at the time of withdrawal) or WF , if failing in their respective courses. Instructors have
```


[3] source: academic_catalog_2024_2025, pages: [104, 105]

```text
action require a student to prove, with supporting documents, that conditions of a medical or
psychological nature, and/or hardship occurred during the semester in question that:
• Had a serious and negative impact on the student’s academic performance.
• Had been reasonably unforeseeable and unavoidable before the last day to officially drop
Al Akhawayn University
www.aui.ma
2024-
2025
105
classes.
A student may request retroactive withdrawal from all courses taken during a given semester or
term by filling out a Retroactive Withdrawal Form. This petition must be accompanied by adequate
documentation and bear all required signatures (the physician’s confirmation of the student’s
health conditions, school dean, DSA, and VPAA). If the retroactive withdrawal request is approved,
the student will be withdrawn from all courses taken that semester with W. The W will indicate a
late withdrawal but will not affect the student’s GPA.
```


[4] source: academic_catalog_2024_2025, pages: [12, 13]

```text
October 25    Last Day for faculty to return the Mid-Semester evaluations
October 29    Last Day to Drop a Course with “W” . Beyond this date
“WP” or  “WF”
November 4-15                    Mandatory Pre-Registration for Spring 2025
(November 6: Green March)
November 6                Holiday: Green March
November 14    Last Day to Drop a Course with “WP” or “WF”
November 18-19     Holiday: Independence Day & long weekend
December 2    Last Day for graduate students to register
for project/thesis defense
December 6     Last Day to Withdraw from the University
December 13                 Last Regular Class Day
FALL
SEMESTER 2024
Al Akhawayn University
www.aui.ma
2024-
2025
13
December 14                    Review Day
December 15-23                     Final Exams (including Common Exams)
December 27                   Final Day for Faculty to Submit Semester Grades
SPRING SEMESTER 2025
January 2-12                          Winter Intersession Program (January 11 -Holiday: Independence
Manifesto Day)
```


[5] source: academic_catalog_2024_2025, pages: [127, 128]

```text
during their tenure in the UHP , and by attending a minimum of two (2) co- and/or extracurricular
activities per academic year, except in cases of study abroad or other institutionally approved
reasons.
Al Akhawayn University
www.aui.ma
2024-
2025
128
• During the graduation academic year (fall or spring semester), prepare and present in front of
peers and UHPC representatives an Exit Research Report on the investigations conducted in the
field of the Admission Research Project Proposal (Guidelines are provided by the UHP Office).
• Note: Honors (and non-Honors) students who take only some of the Honors courses receive
upon request a letter recognizing the extent of their participation.
• Note: An UHP student who does not receive credit toward one of the UHP certificates, but who
receives what would normally be considered a passing grade at AUI, will be considered to have
earned a passing grade toward the ordinary AUI graduation requirements.
Withdrawal Policy
```

