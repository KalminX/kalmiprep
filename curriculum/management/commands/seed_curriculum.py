from django.core.management.base import BaseCommand
from django.utils.text import slugify
from curriculum.models import Subject, Topic, Subtopic

CURRICULUM_DATA = {
    "mathematics": {
        "name": "Mathematics",
        "code": "MATH",
        "color_theme": "math",
        "icon_name": "calculator",
        "order": 1,
        "description": "Fundamental and advanced mathematics covering Number & Numeration, Algebra, Geometry, Trigonometry, Calculus, and Statistics for WAEC, UTME/JAMB, and NECO.",
        "topics": [
            {
                "name": "Number and Numeration",
                "description": "Number bases, modular arithmetic, indices, logarithms, surds, and set theory.",
                "subtopics": [
                    "Number Bases & Conversions",
                    "Modular Arithmetic",
                    "Indices & Logarithms",
                    "Surds & Rationalization",
                    "Sets & Venn Diagrams",
                    "Percentages, Ratio & Proportions",
                ],
            },
            {
                "name": "Algebra",
                "description": "Polynomials, equations, inequalities, variations, sequences, series, and matrices.",
                "subtopics": [
                    "Linear and Quadratic Equations",
                    "Simultaneous Equations",
                    "Sequences and Series (AP & GP)",
                    "Inequalities and Linear Programming",
                    "Variation (Direct, Inverse, Joint)",
                    "Matrices and Determinants",
                    "Binary Operations",
                ],
            },
            {
                "name": "Geometry and Trigonometry",
                "description": "Plane geometry, angles, polygons, circles, coordinate geometry, and trigonometry.",
                "subtopics": [
                    "Lines, Angles and Polygons",
                    "Circle Theorems",
                    "Trigonometric Ratios & Graphs",
                    "Sine & Cosine Rules",
                    "Angles of Elevation & Depression",
                    "Bearings & Distances",
                    "Coordinate Geometry (Lines, Gradients, Distances)",
                ],
            },
            {
                "name": "Calculus",
                "description": "Differentiation, tangents, normals, maxima, minima, and integration applications.",
                "subtopics": [
                    "Limits and First Principles",
                    "Rules of Differentiation",
                    "Applications of Differentiation (Tangents, Maxima, Minima)",
                    "Indefinite and Definite Integration",
                    "Area Under Curves & Kinematic Calculus",
                ],
            },
            {
                "name": "Statistics and Probability",
                "description": "Data representation, central tendency, dispersion, permutations, combinations, and probability.",
                "subtopics": [
                    "Frequency Distributions & Histograms",
                    "Measures of Central Tendency (Mean, Median, Mode)",
                    "Measures of Dispersion (Range, Variance, Standard Deviation)",
                    "Permutations and Combinations",
                    "Theoretical & Experimental Probability",
                ],
            },
        ],
    },
    "chemistry": {
        "name": "Chemistry",
        "code": "CHEM",
        "color_theme": "chem",
        "icon_name": "flask-conical",
        "order": 2,
        "description": "Inorganic, physical, and organic chemistry principles including Atomic Structure, Stoichiometry, Chemical Reactions, Periodicity, and Carbon Compounds.",
        "topics": [
            {
                "name": "Separation of Mixtures & Purification",
                "description": "Pure and impure substances, criteria of purity, and classical laboratory separation techniques.",
                "subtopics": [
                    "Filtration, Evaporation and Crystallization",
                    "Distillation (Simple & Fractional)",
                    "Chromatography",
                    "Sublimation and Solvent Extraction",
                ],
            },
            {
                "name": "Atomic Structure and Periodic Table",
                "description": "Subatomic particles, isotopes, electron configuration, orbitals, and periodic trends.",
                "subtopics": [
                    "Protons, Neutrons, Electrons & Isotopy",
                    "Electronic Configuration & Quantum Shells",
                    "The Periodic Law & Periodic Trends",
                    "Chemical Bonding (Ionic, Covalent, Metallic)",
                    "Intermolecular Forces & Hydrogen Bonding",
                ],
            },
            {
                "name": "Stoichiometry & Mole Concept",
                "description": "Calculations from chemical equations, empirical formulas, gas volumes, and volumetric analysis.",
                "subtopics": [
                    "Mole Concept and Avogadro's Constant",
                    "Empirical and Molecular Formulas",
                    "Molar Mass and Percentage Composition",
                    "Chemical Equations and Stoichiometric Calculations",
                    "Volumetric Analysis & Acid-Base Titrations",
                ],
            },
            {
                "name": "Acids, Bases, and Salts",
                "description": "Properties, pH, buffer solutions, neutralization, preparation and uses of salts.",
                "subtopics": [
                    "Definitions (Arrhenius, Bronsted-Lowry, Lewis)",
                    "The pH Scale & Indicators",
                    "Neutralization and Salt Preparation",
                    "Deliquescence, Efflorescence and Hygroscopy",
                    "Water Hardness and Purification",
                ],
            },
            {
                "name": "Kinetics, Energetics and Equilibrium",
                "description": "Reaction rates, collision theory, enthalpy changes, and chemical equilibrium principles.",
                "subtopics": [
                    "Enthalpy Changes (Exothermic & Endothermic)",
                    "Factors Affecting Reaction Rates",
                    "Chemical Equilibrium & Le Chatelier's Principle",
                    "Energy Profiles & Activation Energy",
                ],
            },
            {
                "name": "Electrochemistry and Redox",
                "description": "Oxidation states, balancing redox reactions, electrolytic and electrochemical cells.",
                "subtopics": [
                    "Oxidation Numbers & Redox Half-Equations",
                    "Electrolysis & Faraday's Laws",
                    "Electrochemical Cells & Standard Electrode Potentials",
                    "Corrosion of Metals & Prevention",
                ],
            },
            {
                "name": "Organic Chemistry",
                "description": "Nomenclature, isomerism, aliphatic and aromatic hydrocarbons, functional groups, and biomolecules.",
                "subtopics": [
                    "Classification and IUPAC Nomenclature",
                    "Alkanes, Alkenes and Alkynes",
                    "Aromatic Hydrocarbons (Benzene)",
                    "Alkanols and Alkanoic Acids",
                    "Esters, Fats and Saponification",
                    "Polymers, Carbohydrates and Proteins",
                ],
            },
        ],
    },
    "physics": {
        "name": "Physics",
        "code": "PHYS",
        "color_theme": "phys",
        "icon_name": "atom",
        "order": 3,
        "description": "Classical and modern physics exploring Mechanics, Heat Energy, Waves, Light, Optics, Electricity, Magnetism, and Nuclear Physics.",
        "topics": [
            {
                "name": "Mechanics and Properties of Matter",
                "description": "Units, vectors, kinematics, dynamics, energy, momentum, circular motion, gravity, and fluids.",
                "subtopics": [
                    "Units, Dimensions and Vector Resolution",
                    "Linear Motion & Equations of Motion",
                    "Newton's Laws and Conservation of Momentum",
                    "Work, Energy and Power",
                    "Circular Motion and Gravitational Fields",
                    "Elasticity & Hooke's Law",
                    "Fluid Pressure, Archimedes' Principle & Flotation",
                ],
            },
            {
                "name": "Thermal Physics",
                "description": "Thermometry, expansion, calorimetry, latent heat, gas laws, and thermal conduction.",
                "subtopics": [
                    "Temperature Scales & Thermometers",
                    "Thermal Expansion in Solids and Liquids",
                    "Specific Heat Capacity and Latent Heat",
                    "Gas Laws (Boyle's, Charles', Pressure Law)",
                    "Heat Transfer (Conduction, Convection, Radiation)",
                ],
            },
            {
                "name": "Waves and Optics",
                "description": "Mechanical and electromagnetic waves, sound, reflection, refraction, lenses, and optical devices.",
                "subtopics": [
                    "Wave Properties, Frequency and Speed",
                    "Sound Waves, Resonance and Beats",
                    "Reflection at Plane and Curved Mirrors",
                    "Refraction of Light and Snell's Law",
                    "Thin Lenses and Optical Instruments",
                    "Dispersion and Electromagnetic Spectrum",
                ],
            },
            {
                "name": "Electricity and Magnetism",
                "description": "Electrostatics, circuits, Ohm's law, magnetic fields, induction, and AC circuits.",
                "subtopics": [
                    "Electrostatics & Coulomb's Law",
                    "Electric Current, Resistance and Ohm's Law",
                    "Series and Parallel Circuits & Kirchhoff's Rules",
                    "Magnetic Fields and Forces on Moving Charges",
                    "Electromagnetic Induction & Transformers",
                    "Alternating Current (AC) Circuits",
                ],
            },
            {
                "name": "Modern Physics and Nuclear Physics",
                "description": "Atomic structure, quanta, photoelectric effect, X-rays, radioactivity, and half-life.",
                "subtopics": [
                    "Atomic Models & Energy Quantization",
                    "Photoelectric Effect and Wave-Particle Duality",
                    "X-Rays & Thermionic Emission",
                    "Radioactivity, Alpha, Beta, Gamma Decay",
                    "Half-Life Calculations & Nuclear Reactions",
                ],
            },
        ],
    },
}


class Command(BaseCommand):
    help = "Seeds foundational curriculum subjects, topics, and subtopics for KalmiPrep"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE(">> Seeding KalmiPrep Curriculum Hierarchy..."))

        total_subjects = 0
        total_topics = 0
        total_subtopics = 0

        for subj_slug, data in CURRICULUM_DATA.items():
            subject, s_created = Subject.objects.update_or_create(
                slug=subj_slug,
                defaults={
                    "name": data["name"],
                    "code": data["code"],
                    "color_theme": data["color_theme"],
                    "icon_name": data["icon_name"],
                    "order": data["order"],
                    "description": data["description"],
                    "is_active": True,
                },
            )
            total_subjects += 1
            status_subj = "Created" if s_created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  [{status_subj}] Subject: {subject.name}"))

            for t_idx, topic_info in enumerate(data["topics"], start=1):
                t_slug = slugify(topic_info["name"])
                topic, t_created = Topic.objects.update_or_create(
                    subject=subject,
                    slug=t_slug,
                    defaults={
                        "name": topic_info["name"],
                        "description": topic_info["description"],
                        "order": t_idx,
                    },
                )
                total_topics += 1

                for st_idx, subtopic_name in enumerate(topic_info["subtopics"], start=1):
                    st_slug = slugify(subtopic_name)
                    Subtopic.objects.update_or_create(
                        topic=topic,
                        slug=st_slug,
                        defaults={
                            "name": subtopic_name,
                            "order": st_idx,
                        },
                    )
                    total_subtopics += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n>> Curriculum Seeding Complete! {total_subjects} Subjects, {total_topics} Topics, {total_subtopics} Subtopics established."
            )
        )
