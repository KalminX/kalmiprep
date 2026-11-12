# Teacher onboarding and classroom assignments

## Account paths

- Staff can invite a tutor or lecture house at `/monetization/staff/invitations/`. The one-time setup URL is emailed, expires after seven days, and activates the teacher profile when accepted. A teacher who already has a KalmiPrep account signs into that account first.
- Any registered user can still apply from Teacher earnings. Those applications stay pending until staff approves them.
- Teacher onboarding is available at `/monetization/onboarding/`; it links profile activation, class creation, assignments, student results, and existing paid tests.

Email settings are read from the deployment environment. In development, Django prints invitation mail to the console. Configure the `EMAIL_*` settings and `DEFAULT_FROM_EMAIL` for production delivery. `TEACHER_TUTORIAL_URL` optionally links a hosted orientation video; cohort or live training is coordinated operationally.

## Classroom workflow

1. An active teacher creates a class and shares its eight-character join code.
2. Students sign into KalmiPrep and join through `/classrooms/`; membership and attempts are tied to their account.
3. Teachers publish free topic drills or four-subject UTME mocks. Every assignment snapshots one eligible question set and shuffles it per student. Full mocks require 60 eligible English questions and 40 from each of three selected elective subjects.
4. Students can resume an in-progress attempt or retake a completed assignment. The teacher results page ranks each student by their best completed percentage, shares tied ranks, shows late completion, and identifies weak subjects/topics. It does not expose student contact details.
5. The teacher results table is server-rendered on entry and then receives authenticated Django Channels updates when students join, start, or complete an attempt. Redis is the shared production channel layer; development can use in-memory channels.

Public paid tests remain a separate optional feature. Classroom assignments do not create Paystack purchases or wallet entries.
