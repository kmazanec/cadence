# Domain Research: AI Fitness Coaching — Screening, Programming, Contraindications, and Compliance

**Confidence summary:** High confidence on screening standards, injury-specific contraindication rules, scope-of-practice boundaries, regulatory classification, and adherence data; medium confidence on three architectural/behavior claims (deep squat exclusion criteria precision, AI failure-mode distribution, KG explainability citation accuracy); low confidence on the 40%/71% personalization-adherence statistics, which are industry marketing figures rather than peer-reviewed results.

---

## 1. Pre-Participation Screening

### The PAR-Q+ as the International Standard

The PAR-Q+ (2021 version) is the internationally recognized pre-participation screening tool that coaches use before writing a single workout. It is a two-tier self-report form: seven yes/no general health questions on page 1, followed by condition-specific follow-up questions on pages 2–3 for anyone who answers "yes" to any page-1 item. Conditions covered include heart disease, hypertension, current medications, arthritis/osteoporosis/back problems, cancer, and mental health conditions.

The three clearance outcomes are:
1. **Unrestricted clearance** — all seven questions answered "no."
2. **Conditional clearance** — one or more "yes" answers that do not reach the medical-referral threshold; a qualified exercise professional may supervise low-to-moderate intensity exercise.
3. **Medical referral** — reserved for a small fraction of respondents (roughly 1%) whose responses indicate high risk. The ePARmed-X+ follow-on tool stratifies these individuals into low/intermediate/high-risk exercise categories.

The form captures only subjective, self-reported information — no measurements, no clinical observation. An AI system that replicates this intake must treat PAR-Q+ responses as client-reported flags, not diagnoses.

Sources: [NASM PAR-Q overview](https://blog.nasm.org/everything-you-need-to-know-about-the-par-q) · [ePARmed-X+](https://eparmedx.com/) · [NutriAdmin PAR-Q guide](https://www.nutriadmin.com/blog/parq-form/) · [PMC validation study](https://pmc.ncbi.nlm.nih.gov/articles/PMC3596208/)

### Movement Screening as a Second Layer

Beyond medical risk, coaches conduct movement-quality assessments before programming: the overhead squat, gait analysis, and single-leg squat. These tools identify muscular imbalances, compensation patterns, and range-of-motion deficits that constrain exercise selection independent of medical history. An overhead squat that reveals knee valgus, for example, suggests weak glutes and tight hip flexors, which must be addressed before loading the pattern.

This is the foundation of NASM's Corrective Exercise Continuum and OPT model: health screening and movement screening are separate, both mandatory layers.

Sources: [NASM movement assessments](https://blog.nasm.org/a-guide-to-movement-assessments) · [NASM OPT model](https://www.nasm.org/certified-personal-trainer/the-opt-model)

### NASM CES Intake Specifics

The NASM Corrective Exercise Specialist intake is the most detailed published template. It collects PAR-Q+ responses, past injury history with kinetic chain effects (ankle sprains alter landing mechanics; knee injuries reduce lumbar proprioception), occupation load factors, sleep and stress, and movement screens scored at five kinetic checkpoints. Surgeries — foot, ankle, knee, back, appendectomy, C-section — are each asked about explicitly because they produce downstream compensations. Red flags requiring immediate medical referral are joint/body swelling (indicating possible internal trauma) and acute sharp pain. Vague complaints such as "my knee hurts a bit" do not automatically trigger referral; they are documented and treated as exercise-modification cues.

Sources: [NASM CES Chapter 7 overview](https://origin.ptpioneer.com/personal-training/certifications/nasm/nasm-ces-chapter-7/) · [NASM assessment resource center](https://www.nasm.org/resource-center/assessment-information) · [NASM movement assessments](https://blog.nasm.org/a-guide-to-movement-assessments)

### ACSM 2015 Screening Update: Removing CVD Risk Factor Count

A key design principle: the ACSM 2015 preparticipation screening update removed cardiovascular risk factor count as a screening trigger. The reasoning was that CVD risk factors are too prevalent in the adult population to serve as a meaningful predictor of the rare events — exercise-related sudden cardiac death or acute myocardial infarction — that screening is meant to catch. The updated model bases screening on (1) current physical activity level, (2) signs/symptoms and known cardiovascular/metabolic/renal disease, and (3) desired exercise intensity. The practical implication for AI system design: requiring medical clearance too broadly creates a false-positive problem that reduces exercise access without improving safety.

Sources: [PubMed 2015 ACSM update](https://pubmed.ncbi.nlm.nih.gov/26473759/) · [Newcastle Sports Medicine summary](https://newcastlesportsmedicine.com.au/wp-content/uploads/2019/06/Updating_ACSM_s_Recommendations_for_Exercise.28.pdf)

---

## 2. Injury Assessment and Ambiguity Resolution

### Structured Pain Assessment: L-DOC-SARA

When a client reports pain, the clinical standard for turning vague complaints into actionable data is the L-DOC-SARA mnemonic: **Location, Duration, Onset, Characteristics, Severity, Aggravating factors, Relieving factors, Associated symptoms.** This framework comes from the International Association for the Study of Pain and is used in clinical pain assessment literature to distinguish pain subtypes (nociceptive, neuropathic, centralized), which have different implications for exercise selection.

For an AI coaching platform, L-DOC-SARA provides the architecture of the clarification loop. A system that asks only "do you have any injuries?" cannot reliably identify contraindications.

Sources: [NCBI pain assessment chapter](https://www.ncbi.nlm.nih.gov/books/NBK556098/) · [IASP pain assessment resources](https://www.iasp-pain.org/resources/topics/pain-assessment-and-measurements/)

### The Ambiguity Problem: AI Cannot Resolve Mislabeled Symptoms

Human coaches use iterative follow-up questioning when a client describes symptoms ambiguously. A physiotherapist "will delve into the specifics of your symptoms and ask a lot of follow up questions, not just go off your perception of what you are feeling." The AI failure mode: if a client describes sharp muscle pain as "nerve pain," a standard LLM generates sciatica-specific guidance that may be entirely wrong for the actual condition. The AI cannot observe compensatory movement, emotional cues, or context.

The architectural conclusion: the clarification loop before programming is load-bearing. Safe contraindication filtering cannot rely on a single ambiguous utterance.

Sources: [The Injury and Performance Clinic (AI physiotherapy limits)](https://www.theinjuryandperformanceclinic.co.uk/blog/can-ai-tools-like-chatgpt-help-with-physiotherapy-and-sports-injury-advice) · [NESTA emergency injury assessment](https://www.nestacertified.com/what-to-do-in-an-emergency-injury-assessment-procedures-for-trainers-coaches/)

### SOAP Notes as the Ongoing Injury Record

SOAP notes (Subjective, Objective, Assessment, Plan) are the standard documentation format for tracking injury status across sessions. The Subjective field captures client-reported symptoms verbatim without interpretation. The Objective field captures observable changes. The Assessment field identifies patterns. The Plan field documents contraindications explicitly — for example: "Client's physical therapist communicated that client may progress from open-chain to closed-chain exercises" or "Client is advised to perform only low-impact aerobic activities to minimize left ankle aggravation." The ACSM Code of Ethics requires trainers to maintain this written record from pre-screening through each session.

This session-by-session record is how injury status evolves over time. A static intake form is not sufficient for ongoing injury-aware programming.

Sources: [IDEA Fit SOAP notes](https://www.ideafit.com/taking-soap-notes/) · [Sprypt SOAP templates](https://www.sprypt.com/blog/free-soap-note-templates-for-athletic-trainers)

### Coach Pain-Communication Protocol: Traffic-Light Scale

Coaches use a structured traffic-light or numerical pain scale — not diagnostic interpretation — when assessing ongoing pain. They ask: location, when it began, acute vs. chronic, and current pain level. Industry guidance explicitly warns against "scaring clients into believing they have a serious disc injury when we have absolutely no grounds." Any movement causing pain is avoided; referral to a healthcare provider is required when pain persists two to four weeks or is described as sharp or intense. The documentation captures pain level and location — not a diagnosis.

An AI system must model injury information at the level trainers actually collect it: pain location + intensity + onset + duration.

Sources: [PTDC corrective exercise and pain guide](https://www.theptdc.com/articles/a-corrective-exercise-specialists-guide-to-training-clients-through-pain-and-injury) · [NFPT injury adjustment guide](https://nfpt.com/making-program-adjustments-when-client-is-injured/)

---

## 3. Exercise Contraindications by Injury Region

The three body regions generating the largest volume of exercise modification protocols in NSCA, NASM, and ACSM curricula are knee pathologies, rotator cuff and shoulder impingement, and lower back conditions. A contraindication filter must have the highest coverage density in these three areas.

Sources: [NSCA knee guidelines](https://www.nsca.com/education/articles/kinetic-select/knee-movement-and-exercise-guidelines/) · [PMC shoulder review](https://pmc.ncbi.nlm.nih.gov/articles/PMC3945046/) · [Deuk Spine herniated disc](https://deukspine.com/blog/lifting-weights-with-herniated-disc/)

### Knee: Contraindications Are Defined by Angle and Kinetic Chain, Not Just Exercise Name

NSCA guidelines specify:

- **Anterior knee pain (patellofemoral pain):** closed-chain movements beyond 90° knee flexion are contraindicated; open-chain movements in the 0°–30° flexion range are contraindicated.
- **ACL reconstruction:** open-chain movements below 45° flexion (end-range leg extensions) are contraindicated. Peak ACL strain occurs at 10°–30° knee flexion. Non-weight-bearing knee extension isolates ACL strain at vulnerable angles (158–396 N for open-chain seated knee extension vs. 0–253 N for most weight-bearing exercises). Progressions should start in the 50°–100° flexion range.
- **Total knee arthroplasty:** closed-chain movements beyond 100° flexion are contraindicated.

The same exercise — a squat — may be safe at one depth and contraindicated at another. A contraindication filter must encode joint angle and kinetic chain type as attributes, not just exercise-level flags.

Sources: [NSCA knee guidelines](https://www.nsca.com/education/articles/kinetic-select/knee-movement-and-exercise-guidelines/) · [PMC ACL clinical review (PMC9897005)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9897005/) · [PMC deep squat review (PMC11618833)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618833/)

### Knee: Patellofemoral Load Depends on Exercise Variant, Not Just Exercise Category

Patellofemoral compressive forces peak at 90° knee flexion. Wall squats with knees positioned over feet produce approximately 2,900 N of patellofemoral stress compared to approximately 3,650 N with knees forward. Side lunges load the patellofemoral joint more than forward lunges at 50°–100°. Stationary lunges produce less load than stepping lunges. The same exercise, performed with different technique, has a different contraindication status. The knowledge graph must encode exercise-variant edges, not just exercise-level edges.

Sources: [PMC patellofemoral biomechanics (PMC4901792)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4901792/) · [PMC ACL clinical review (PMC9897005)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9897005/)

### Knee: Deep Squats — Nuanced Evidence, Not a Blanket Contraindication (medium confidence on exclusion-criteria details)

**Flagged: medium confidence.** A 2024 scoping review of 15 studies found 87% concluded deep squats are safe for healthy knee joint health when performed with correct technique. The review explicitly excluded injured populations, but the precise list of excluded conditions requires care: meniscus tears, chondromalacia, cartilage damage, and ligament strains were stated exclusions; whether ACL injuries and patellofemoral pain were formally listed as exclusion criteria or were simply absent from included samples is less certain in the reported text. The core conclusion holds regardless: the safety evidence does not transfer to injured populations, and an AI system trained on "deep squats are safe" literature without injury-specific filtering would produce false negatives.

There is also a countervailing biomechanical finding: at full depth, contact between the back of the thigh and calf reduces knee compressive forces by approximately 30%. A blanket rule banning deep squats for all knee conditions would be an over-restriction for healthy or fully recovered members.

Sources: [PMC deep squat scoping review (PMC11618833)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11618833/) · [PMC patellofemoral biomechanics (PMC4901792)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4901792/)

### Shoulder: Internal Rotation Under Load at or Above 90° Abduction Is the Core Contraindication

Behind-the-neck pulldowns and presses force extreme external rotation with horizontal abduction while the shoulder is elevated, causing the supraspinatus tendon to fold over the acromial edge. Internally-rotated lateral raises drive the humerus into the acromion. Deep dips and upright rows are consistently flagged. Overhead pressing in general is not universally contraindicated for impingement but is high-risk without adequate mobility.

Safe alternatives include partial-range-of-motion pressing, neutral-grip variations, and below-horizontal pulling. Approximately 90% of shoulder impingement cases can be managed conservatively, and exercise selection is therapeutic — wrong selection is iatrogenic. The JOSPT 2024 systematic review confirmed exercise therapy as the primary intervention for rotator cuff conditions.

Sources: [PMC shoulder review (PMC3945046)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3945046/) · [Pliability shoulder impingement guide](https://pliability.com/stories/shoulder-impingement-exercises-to-avoid) · [Jacksonville Orthopaedic Institute](https://www.joionline.net/library/the-top-5-worst-shoulder-exercises-to-avoid-lateral-raises-and-more/) · [HighBar Health rotator cuff](https://www.highbarhealth.com/movements-to-avoid-with-rotator-cuff-injury/) · [JOSPT rotator cuff systematic review](https://www.jospt.org/doi/10.2519/jospt.2024.12453)

### Lower Back: Herniation and Stenosis Have Partially Opposite Contraindication Profiles

Treating all "lower back injury" as a single category produces both false positives and false negatives.

- **Lumbar disc herniation:** the primary contraindication is spinal flexion under load, especially combined with rotation. Contraindicated movements include rounded deadlifts, full sit-ups, good mornings, leg press with lumbar flexion, and any combined flexion-torsion pattern. Combining lifting with twisting markedly reduces the nuclear pressure required to form clinically relevant radial tears.
- **Spinal stenosis:** the primary contraindication is extension-loading that further narrows the spinal canal. Contraindicated movements include cobra/upward-dog yoga poses, overhead press with lumbar hyperextension, back extensions with hyperextension, and high-impact activities (running, jumping). Flexion-based decompression exercises, which are problematic for herniation patients, may actually be appropriate for stenosis patients.

A knowledge graph that encodes "lower back injury" as a single node will get this wrong in both directions. The graph must distinguish injury subtypes as separate nodes with different edge sets.

Sources: [Deuk Spine herniated disc](https://deukspine.com/blog/lifting-weights-with-herniated-disc/) · [Spine-health herniation exercises](https://www.spine-health.com/blog/exercises-avoid-lumbar-herniation) · [PMIR spinal stenosis](https://paininjuryrelief.com/spinal-stenosis-exercises-avoid-start/) · [South Florida Back Spine stenosis](https://southfloridabackspineandscoliosis.com/lumbar-stenosis-exercises-to-avoid-and-recommendations/) · [PMC lower back review (PMC8402067)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8402067/) · [Doctronic spondylolisthesis](https://www.doctronic.ai/blog/7-exercises-you-must-avoid-if-you-have-spondylolisthesis/) · [Premia Spine L5-S1](https://premiaspine.com/l5-s1-exercises-to-avoid/)

---

## 4. Exercise Programming Standards

### NASM OPT Model: Phase-Appropriate Parameters

NASM's Optimum Performance Training model defines the dominant session-level programming constraints for recreational clients across five phases:

| Phase | Type | Sets | Reps | Intensity | Tempo | Rest |
|---|---|---|---|---|---|---|
| 1 | Stabilization Endurance | 1–3 | 12–20 | 50–70% 1RM | 4/2/1 | 0–90 sec |
| 2 | Strength Endurance | 2–4 | 8–12 (16–24/superset) | — | — | — |
| 3 | Hypertrophy | 3–5 | 6–12 | 75–85% 1RM | — | — |
| 4 | Maximal Strength | 4–6 | 1–5 | 85–100% 1RM | — | — |

Phase changes occur every four to six weeks, or earlier if a plateau occurs. A workout generator must stay within these phase-appropriate bounds or output will be either unsafe (too much intensity for beginners) or ineffective (too little stimulus for advanced clients). Movement balance constraints — push/pull ratio, anterior/posterior chain balance — are an additional implicit requirement.

Sources: [NASM OPT model](https://www.nasm.org/certified-personal-trainer/the-opt-model) · [NASM periodization simplified](https://blog.nasm.org/periodization-training-simplified) · [NASM Phase 1 overview](https://blog.nasm.org/off-to-a-great-start-phase-1-and-the-new-novice-client)

### ACSM 2026 Resistance Training Guidelines

The 2026 ACSM Position Stand — the first update in 17 years, based on 137 systematic reviews and over 30,000 participants — recommends 10 sets per muscle group per week as the hypertrophy-optimal target for recreational clients. Four sets per week is the minimum effective dose; diminishing returns appear above 20 sets per week. For strength, 80% 1RM for two to three sets per exercise. All major muscle groups should be trained at least twice weekly. The guidelines explicitly state that complex periodization did not consistently outperform simpler approaches for healthy recreational adults — consistency is a stronger determinant of outcomes than program structure.

Sources: [ACSM 2026 resistance training guidelines](https://acsm.org/resistance-training-guidelines-update-2026/) · [Medical News Today summary](https://www.medicalnewstoday.com/articles/new-resistance-training-guidelines-debunk-myths-stronger-muscles-strength-size) · [2 Minute Medicine summary](https://www.2minutemedicine.com/landmark-acsm-mcmaster-guidelines-simplify-resistance-training-for-longevity/)

### Periodization Models by Experience Level

For recreational clients, the appropriate periodization model depends on training history:

- **Beginners:** linear periodization — gradually increasing intensity while decreasing volume across four- to six-week blocks. Simplicity and progressive overload minimize injury risk.
- **Intermediate clients:** daily undulating periodization (DUP) — varying intensity and volume within a week or across sessions (e.g., day 1 high-volume/low-intensity, day 3 low-volume/high-intensity). Appropriate for clients who have adapted to linear stimulus.
- **Performance athletes with competition timelines:** block periodization — not typically appropriate for a general fitness population.

For rehab contexts specifically, autoregulation via RPE (Rating of Perceived Exertion) is preferable over percentage-based intensity prescription because establishing a true 1RM may be contraindicated during active healing phases. A workout generator must branch its intensity-prescription logic: percentage-based for healthy members, RPE-based for members in active recovery.

Sources: [NFPT periodization](https://nfpt.com/simplifying-periodization-training-for-any-audience/) · [PMC periodization for sports PTs (PMC4637911)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4637911/) · [NASM periodization simplified](https://blog.nasm.org/periodization-training-simplified) · [Set for Set periodization models](https://www.setforset.com/blogs/news/periodization-training-models) · [Physical Coaching Academy](https://www.physicalcoachingacademy.com/en/blog/post/periodization-linear-or-undulating-for-your-clients)

---

## 5. Scope of Practice and Legal Boundaries

### What Personal Trainers May and May Not Do

NFPT, NASM, NSCA, and ACE all define the same outer boundary: personal trainers may not diagnose medical conditions, prescribe medical interventions, or provide rehabilitation services. When a client has an injury, trainers receive guidelines from a physician or physical therapist and follow them. They do not generate clinical judgments.

The legally operative distinction for an AI coaching platform: if a system says "you have patellofemoral syndrome," that is a diagnosis. If it says "based on your reported knee pain, we are avoiding deep knee flexion exercises," that is fitness coaching. The line between these must be enforced by language choices, not just architectural intent.

Sources: [NFPT scope of practice](https://nfpt.com/legal-ethical-scope-of-practice) · [Brook Bushi scope of practice](https://brookbushinstitute.com/articles/certification-cannot-change-movement-professional-scope-of-practice) · [ACE PT Manual Ch. 1](https://www.acefitness.org/academy/AcademyElitePDFs/ACE_PT5th_Manual_Ch1.pdf) · [Fit Legally scope](https://www.fitlegally.com/blogs/news/fitness-professionals-are-you-giving-medical-advice) · [CPHINS scope](https://cphins.com/scope-of-practice-issues-for-fitness-professionals/) · [APTA scope](https://www.apta.org/your-practice/scope-of-practice)

### The Regulatory Vacuum: Personal Training Is Almost Entirely Unregulated

In the United States, no federal licensing exists for personal trainers. Certification is voluntary (NASM, NSCA, ACE, ACSM). Only two jurisdictions impose state-level licensing requirements: Louisiana (Clinical Exercise Physiologists, since 1996) and Washington DC (Personal Fitness Training, since 2014). An AI-generated fitness platform inherits this regulatory vacuum — there is no federal body governing the quality or safety of exercise prescriptions from AI systems either. However, overstepping into medical diagnosis, rehabilitation prescription, or supplement prescription can expose trainers, and by extension AI platforms, to criminal charges and civil liability.

Sources: [CPHINS scope](https://cphins.com/scope-of-practice-issues-for-fitness-professionals/) · [National Law Review personal training regulation](https://natlawreview.com/article/personal-training-historically-unregulated-occupation-change-horizon) · [Elements System scope PDF](https://elementssystem.com/wp-content/uploads/2018/06/Scope.pdf)

---

## 6. Regulatory and Compliance Landscape

### FDA Classification: Wellness App vs. Software as a Medical Device

An AI fitness coaching app remains outside FDA medical device oversight as long as it does not diagnose, treat, or prevent disease, and allows independent review of any recommendation. The FDA distinguishes wellness software (step counters, general fitness tracking) from Software as a Medical Device (SaMD) by intended use.

A fitness app that uses language like "support" or "track" avoids regulation; one that claims to "treat" or "diagnose" triggers Class II/III SaMD oversight. Critically, marketing language is as determinative as technical capability. An injury-aware coaching platform flagging exercises as "not recommended given your history" is probably safe; claiming that the platform "prevents re-injury of your ACL" could trigger SaMD classification. The FDA's June 2023 guidance on device software functions and 2024 adaptive AI guidance tightened documentation requirements but did not expand the wellness app exemption.

Sources: [FDA digital health overview](https://www.dspadvocates.com/post/digital-health-and-the-fda-when-software-becomes-a-medical-device) · [ICLG USA digital health](https://iclg.com/practice-areas/digital-health-laws-and-regulations/usa) · [Enlil FDA SaMD guidelines](https://enlil.com/blog/fda-software-as-a-medical-device-guidelines-explained/) · [Telehealth.org FDA AI oversight](https://telehealth.org/news/fda-clarifies-oversight-of-ai-health-software-and-wearables-limiting-regulation-of-low-risk-devices/) · [Arnold Porter CDS guidance](https://www.arnoldporter.com/en/perspectives/advisories/2026/01/fda-cuts-red-tape-on-clinical-decision-support-software)

### FTC Health Breach Notification Rule and Algorithmic Disgorgement (medium confidence on timeline details)

Health apps that store personal health data but are not covered by HIPAA still face FTC oversight under the Health Breach Notification Rule. The FTC's enforcement posture includes algorithmic disgorgement as an established remedy — meaning an AI fitness platform that trains its recommendation model on data obtained without proper consent could be forced to delete that model entirely. **Flagged: medium confidence on timeline.** The disgorgement tool is well-established: the FTC first applied it in 2019 (Cambridge Analytica), then in 2021 (Everalbum), 2022 (WW International/Kurbo), and 2023 (Edmodo). The 2024 HBNR update expanded notification scope to health apps but did not introduce disgorgement as a new enforcement tool, as earlier drafts of these findings stated.

Sources: [ICLG USA digital health](https://iclg.com/practice-areas/digital-health-laws-and-regulations/usa) · [DSP Advocates FDA/FTC overview](https://www.dspadvocates.com/post/digital-health-and-the-fda-when-software-becomes-a-medical-device)

### HIPAA Does Not Apply to Standalone Fitness Apps

HIPAA applies to covered entities (healthcare providers, insurers) and their business associates. A standalone fitness coaching app that does not integrate with a covered healthcare provider's systems is not a covered entity and is not subject to HIPAA. The FTC Health Breach Notification Rule may apply if the app collects health information and experiences a breach, but routine HIPAA compliance obligations do not apply to standalone wellness products.

**Flagged: single source.** This finding rests on one primary source.

Sources: [Dickinson-Wright app user HIPAA](https://www.dickinson-wright.com/news-alerts/app-users-beware)

### AI Fitness Coaching Liability Is Legally Unresolved

No established legal framework exists for AI-specific fitness coaching liability. Product liability theories could apply to the developer; negligence theories to the deploying company; waiver and assumption-of-risk frameworks could implicate the user. Unlike human trainers, AI systems are not certified and have no established duty-of-care standards. This legal ambiguity has direct architectural implications: the system must include strong disclaimers, referral-out logic for high-risk conditions, and documented evidence that contraindicated exercises are excluded — both as a safety measure and as a legal paper trail.

Sources: [Score Detect AI fitness legality](https://www.scoredetect.com/blog/posts/the-legality-of-ai-generated-fitness-coaching-explored) · [Telehealth.org FDA AI oversight](https://telehealth.org/news/fda-clarifies-oversight-of-ai-health-software-and-wearables-limiting-regulation-of-low-risk-devices/)

---

## 7. AI Failures in Exercise Recommendation

### Current AI Chatbots Are High on Accuracy but Low on Completeness

A 2024 JMIR study of AI chatbot exercise recommendations found overall accuracy of 90.7% but comprehensiveness of only 41.2%. FITT principle components were almost entirely absent: frequency was fully present in 8% of outputs, intensity in 8%, time in 4%, and volume in 0%. **Flagged: single source** for these specific statistics; the study is peer-reviewed but not yet independently replicated.

The dominant safety failure was false-positive over-caution: the AI recommended unnecessary medical clearance for healthy adults (53% of errors) and contraindicated heavy lifting for hypertensive individuals when ACSM guidelines do not prohibit this given adequate progression and the absence of underlying disease. Readability averaged college-level (grade 13.7) versus the recommended sixth-grade reading level for patient materials.

Sources: [JMIR AI chatbot exercise recommendations](https://mededu.jmir.org/2024/1/e51308)

### The Dominant Failure Mode: False-Positive Over-Caution Combined with Hallucinated Rationale (medium confidence on distribution)

**Flagged: medium confidence.** The available evidence suggests AI systems over-restrict rather than under-restrict in most cases — but the balance between false positives (blocking safe exercises) and false negatives (allowing contraindicated ones) has not been systematically measured across representative fitness AI deployments. What is well-established is that hallucinated rationale is a real phenomenon: across general AI mobile apps, 38% of user-reported hallucinations are factual incorrectness and 15% are fabricated information — leading to reasoning that sounds clinical but is unsourced.

The architectural implication is bidirectional: the knowledge graph must have complete contraindication coverage to prevent false negatives, while the generation layer must not hallucinate restrictions that are not in the graph.

Sources: [JMIR AI chatbot study](https://mededu.jmir.org/2024/1/e51308) · [PMC AI hallucination review (PMC12365265)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12365265/)

### The Deeper Failure: Generic Programming Without Individual Context

Multiple sources converge on a more fundamental failure mode: AI fitness apps work from incomplete data representations. The JMIR 2025 scoping review of LLM-based exercise coaches found that "the inherent black-box nature of many LLMs presents a major barrier to explainability, eroding the trust of both users and clinicians." The IDEA Health & Fitness Association analysis and industry commentary identify the core problem: the AI sees a static snapshot of the client, while a human coach sees evolving movement quality, compensatory patterns, emotional state, and fatigue in real time. The failure is not specifically false positives or false negatives — it is the absence of the iterative assessment loop that a human coach continuously performs.

Sources: [IDEA Fit AI safety](https://www.ideafit.com/is-ai-safe-for-fit-pros/) · [JMIR scoping review 2025](https://www.jmir.org/2025/1/e79217) · [Human Prompts exercise form AI](https://thehumanprompts.com/ai-app-to-check-exercise-form/)

---

## 8. Explainability and Coach Trust

### What Coaches Actually Need: Plain-Language Rationale, Not Graph Traces (medium confidence)

**Flagged: medium confidence.** Coaches reviewing AI-generated programs need to explain exercise choices to clients in plain language. Industry sources emphasize that AI tools for coaches should "explain coaching concepts" and "provide crucial background knowledge." The meaningful output is a sentence such as "we're avoiding leg extensions because your ACL is reconstructed and open-chain knee extension below 45° is contraindicated" — not a raw graph-path notation. The architecture should generate graph-grounded natural language rationale, not expose backend edge traversals.

This finding is plausible and consistent with general human-computer interaction principles, but no controlled study of coach acceptance of AI-generated fitness programs has been published.

Sources: [Simplifaster AI coaches guide](https://simplifaster.com/articles/embracing-ai-a-coachs-guide-to-transforming-your-practice/) · [ICF AI coaching blog](https://coachingfederation.org/blog/9-ways-coaches-can-use-ai-to-enhance-and-expand-their-coaching-practice/)

### Knowledge Graph Path Tracing Supports Explainability, But No Fitness-Domain User Trust Study Exists

Graph paths can be rendered as natural-language sentences — this is demonstrated in the KPRN paper (e.g., "X is recommended because you listened to Y by the same artist"). The KG4EER system applies this to exercise recommendation. However, all published evaluation uses technical metrics (hit@K, NDCG). No user trust studies or coach acceptance studies in the fitness coaching context have been published. The claim that graph path tracing is sufficient for coach explainability is architecturally plausible but empirically unvalidated.

The 2025 JMIR scoping review identified lack of explainability as the primary adoption barrier for LLM-based exercise coaches and recommended RAG-based grounding in clinical guidelines as the mitigation. It also proposed an "Adaptive Precise Boolean Framework" — decomposing complex safety criteria into yes/no questions — as a way to make AI logic auditable by coaches.

Sources: [KPRN explainability paper](https://ar5iv.labs.arxiv.org/html/1811.04540) · [KG4EER exercise recommendation](https://www.sciencedirect.com/science/article/pii/S0893608024008839) · [JMIR scoping review 2025](https://www.jmir.org/2025/1/e79217) · [Springer AI coaching explainability](https://link.springer.com/article/10.1007/s44443-025-00173-5)

---

## 9. Knowledge Graph Architecture for Fitness

### Existing Fitness KG Systems: Entity Types and a Gap in Injury Modeling

Published fitness knowledge graph systems (FitKG-CN, R-CKGAT) use eight entity types: body parts, technical terms, exercise items, athletic goals, fitness movements, nutrients, instruments/tools, and anatomic structures; and 11 relationship types. However, injury contraindication modeling is explicitly absent from these systems. The R-CKGAT paper (PMC12122711) does not detail specific mechanisms for encoding contraindications or safety restrictions. The Neo4j fitness recommendation reference handles "Physical Limitations" as a separate filter node rather than as rich injury-to-exercise contraindication edges with angle and kinetic chain attributes.

This is a gap that must be filled by the architecture under design: the existing literature provides the entity and relationship vocabulary but not the contraindication subgraph.

Sources: [R-CKGAT fitness KG (PMC12122711)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12122711/) · [Neo4j fitness recommendation](https://neo4j.com/blog/healthcare/fitness-program-recommendation-engine/)

### GraphRAG Outperforms Naive RAG on Multi-Hop Reasoning

GraphRAG (graph-based retrieval augmented generation) outperforms naive RAG on multi-hop reasoning and domain-specific retrieval by leveraging entity relationships for graph-guided retrieval before generation. The workflow is three-stage: Graph-Based Indexing → Graph-Guided Retrieval → Graph-Enhanced Generation. For a fitness contraindication system, the retrieval step can traverse injury → joint → exercise paths to pull relevant context before generating a recommendation, grounding LLM output in explicit graph relationships rather than unstructured similarity search.

**Flagged: medium confidence on magnitude of advantage.** The directional claim is well-supported by multiple 2024 arXiv surveys; the degree of improvement is task-dependent and has not been measured specifically for fitness contraindication retrieval.

Sources: [GraphRAG survey (arXiv 2408.08921)](https://arxiv.org/abs/2408.08921) · [GraphRAG survey (arXiv 2501.00309)](https://arxiv.org/abs/2501.00309) · [IBM GraphRAG overview](https://www.ibm.com/think/topics/graphrag)

### R-CKGAT: KG Triplets Serve Dual Purposes (medium confidence on second citation)

**Flagged: medium confidence.** The R-CKGAT paper (PMC12122711) demonstrates that knowledge graph triplets serve dual purposes: traceable explanatory paths for recommendations and cross-entity preference inference. A second cited source (PMC11410769) focuses on LIME and SHAP post-hoc explanation methods rather than graph-based explanations; the claim that it supports graph paths as "potentially ideal explanations for recommender systems" is not verified from that paper's actual content. The architectural conclusion — graph paths as the explainability backbone, with natural language wrapping for coaches — remains plausible and is supported by PMC12122711 independently.

Sources: [R-CKGAT fitness KG (PMC12122711)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12122711/) · [NCM XAI review (PMC11410769)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11410769/)

---

## 10. User Adherence and Retention

### Dropout Rates Are Severe: Most Users Leave Within Weeks

**Flagged: medium confidence on specific percentages.** A 2026 JMIR cross-sectional study documented session volume dropping 69.3% by month one and 80.6% by month three in a fitness app's user base. The broader mobile health literature reports that up to 98% of fitness app users use the app for only a short period. These figures come from a single JMIR study and the 98% figure is commonly cited in industry contexts without a single definitive primary source.

Sources: [JMIR fitness app adherence 2026 (PMC12828317)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12828317/)

### Early Consistency Is the Strongest Predictor of Long-Term Adherence

Training consistency in the first 28 days is the dominant predictor of six-month and twelve-month adherence, stronger than sex, age, or equipment diversity. A SportRxiv preprint analyzing 522,000+ fitness app users found only 18.1% of beginner users remained adherent (at least one session per week) at six months, with median dropout at 14 weeks. A deep learning study using 90-day behavioral data achieved 87% accuracy and 85% F1 score predicting month-4 adherence, with number of missed workouts as the highest-weight feature.

Sources: [SportRxiv large-scale adherence study](https://sportrxiv.org/index.php/server/preprint/view/709) · [PMC deep learning adherence prediction (PMC8535546)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8535546/)

### Adherence Has Four Distinct Components That Respond to Different Factors

Research identifies four separable adherence constructs: session completion (sessions done divided by sessions prescribed), attendance rate, duration adherence, and intensity adherence. A user can attend a session but not complete it, or complete it but at lower-than-planned intensity. Frequency-based adherence (sessions per week vs. plan) is the most commonly tracked proxy in app-based platforms. Critically, "adherence, retention, and frequency do not respond to the same factors" — different system features are needed to address each.

Long-term adherence rates by demographic: beginners at six months 18.1%, older users (51+) 23.8%, males 19.9% vs. females 15.2%, intermediate users 28.6%, advanced users 38.2%. Resistance training showed higher adherence (mean EARS score 66.46) than aerobic (60.91) or flexibility training (53.36).

Sources: [PMC adherence components (PMC4932302)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4932302/) · [Frontiers Sports adherence review (PMC10694453)](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2023.1293535/full) · [JMIR fitness app adherence (PMC12828317)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12828317/) · [SportRxiv large-scale adherence](https://sportrxiv.org/index.php/server/preprint/view/709)

### Personalization-Adherence Statistics Are Low Confidence

**Flagged: low confidence.** Claims that users following AI-guided personalized training show 40% higher adherence to fitness goals versus generic programming, and that 71% of published research shows AI chatbots increase exercise frequency, come from a single industry statistics article (create.fit, 2025) citing market research rather than controlled clinical trials. The directional claim — that personalization improves adherence — is well-supported in the literature. The specific percentages should be treated as marketing figures until independently verified.

Sources: [Create.fit AI training statistics](https://create.fit/blogs/ai-personal-training-statistics/)

### FMS: Corrective Exercise Guide, Not Injury Risk Predictor

Modern meta-analytic evidence has weakened the original FMS claim that low scores predict injury risk. The overhead squat test does reliably identify movement deficits — ankle mobility, hip flexibility, shoulder mobility — that inform exercise selection and regression. For a workout generator, FMS-like screening identifies which movement patterns to avoid or modify, even if it does not reliably predict injury probability numerically.

**Flagged: medium confidence.** The literature on FMS predictive validity is contested and evolving.

Sources: [Output Sports FMS analysis](https://www.outputsports.com/blog/functional-movement-screen-how-coaches-can-go-beyond-the-basics-with-digital-testing) · [Meloq FMS tests](https://meloqdevices.com/blogs/meloq-updates/functional-movement-screen-tests)

---

## References

All inline citations are linked directly within the relevant sections above. Key primary sources:

- ePARmed-X+ tool: https://eparmedx.com/
- PAR-Q+ validation: https://pmc.ncbi.nlm.nih.gov/articles/PMC3596208/
- ACSM 2015 screening update: https://pubmed.ncbi.nlm.nih.gov/26473759/
- ACSM 2026 resistance training: https://acsm.org/resistance-training-guidelines-update-2026/
- NSCA knee guidelines: https://www.nsca.com/education/articles/kinetic-select/knee-movement-and-exercise-guidelines/
- PMC ACL clinical review: https://pmc.ncbi.nlm.nih.gov/articles/PMC9897005/
- PMC patellofemoral biomechanics: https://pmc.ncbi.nlm.nih.gov/articles/PMC4901792/
- PMC deep squat scoping review: https://pmc.ncbi.nlm.nih.gov/articles/PMC11618833/
- JOSPT rotator cuff 2024: https://www.jospt.org/doi/10.2519/jospt.2024.12453
- PMC periodization for sports PTs: https://pmc.ncbi.nlm.nih.gov/articles/PMC4637911/
- JMIR AI chatbot exercise accuracy: https://mededu.jmir.org/2024/1/e51308
- JMIR LLM exercise coach scoping review: https://www.jmir.org/2025/1/e79217
- R-CKGAT fitness KG: https://pmc.ncbi.nlm.nih.gov/articles/PMC12122711/
- GraphRAG survey: https://arxiv.org/abs/2408.08921
- SportRxiv large-scale adherence: https://sportrxiv.org/index.php/server/preprint/view/709
- PMC deep learning adherence prediction: https://pmc.ncbi.nlm.nih.gov/articles/PMC8535546/
- NCBI L-DOC-SARA pain assessment: https://www.ncbi.nlm.nih.gov/books/NBK556098/
