import json
from pathlib import Path
from django.core.management.base import BaseCommand
from curriculum.models import Subject, Topic


TOPIC_NAME_OVERRIDES = {
    "algebra": "Algebra",
    "geometry-and-trigonometry": "Geometry and Trigonometry",
    "number-bases": "Number Bases",
    "indices": "Indices",
    "logarithms": "Logarithms",
    "surds": "Surds",
    "number-and-numeration": "Number and Numeration",
    "fractions-decimals-percentages-and-approximation": "Fractions, Decimals, Percentages & Approximation",
    "sets": "Sets & Set Operations",
    "logic": "Mathematical Logic",
    "modular-arithmetic": "Modular Arithmetic",
    "positive-and-negative-integers": "Positive and Negative Integers",
    "rational-numbers": "Rational Numbers",
    "matrices-and-determinants": "Matrices and Determinants",
    "ratios-proportions-and-rates": "Ratios, Proportions and Rates",
    "financial-arithmetic": "Financial Arithmetic",
    "variations": "Variations",
    "simple-operations-on-algebraic-expression": "Operations on Algebraic Expressions",
    "solution-of-linear-equations": "Linear Equations",
    "change-of-subject-of-formula": "Change of Subject of Formula",
    "quadratic-equations": "Quadratic Equations",
    "graph-of-linear-and-quadratic-functions": "Graphs of Linear & Quadratic Functions",
    "linear-inequalities": "Linear Inequalities",
    "algebraic-fractions": "Algebraic Fractions",
    "functions-and-relations": "Functions and Relations",
    "polynomials": "Polynomials",
    "progressions": "Progressions (AP & GP)",
    "binary-operations": "Binary Operations",
    "mensuration": "Mensuration",
    "lengths-and-perimeters": "Lengths and Perimeters",
    "areas": "Areas of Plane Figures",
    "volumes": "Volumes of Solids",
    "angles-and-intercepts-on-parallel-lines": "Angles & Parallel Lines",
    "triangles-and-polygons": "Triangles and Polygons",
    "circles": "Circles & Circle Theorems",
    "construction": "Geometric Construction",
    "coordinate-geometry-of-straight-lines": "Coordinate Geometry",
    "trigonometric-ratios": "Trigonometric Ratios",
    "angles-of-elevation-and-depression": "Angles of Elevation & Depression",
    "bearings-and-distances": "Bearings and Distances",
    "calculus": "Calculus",
    "differentiation": "Differentiation",
    "application-of-differentiation": "Application of Differentiation",
    "integration": "Integration",
    "statistics": "Statistics",
    "representation-of-data": "Representation of Data",
    "measures-of-location": "Measures of Location (Mean, Median, Mode)",
    "measures-of-dispersion": "Measures of Dispersion (Range, Variance, Standard Deviation)",
    "permutation-and-combination": "Permutation and Combination",
    "probability": "Probability",
    "application-of-integration": "Application of Integration",
    
    # Physics
    "heat-energy": "Heat Energy & Temperature",
    "thermodynamics": "Thermodynamics & Gas Laws",
    "wave": "Waves & Wave Motion",
    "field": "Gravitational & Magnetic Fields",
    "light-and-optics": "Light & Geometrical Optics",
    "atomic-physics": "Atomic & Nuclear Physics",
    "concept-of-field": "Concepts of Fields",
    "work-energy-power": "Work, Energy and Power",
    "linear-motion": "Linear Motion & Kinematics",
    "equilibrium-of-forces-1": "Equilibrium of Forces",
    
    # Chemistry
    "matter-and-separation-techniques": "Matter & Separation Techniques",
    "particulate-nature-of-matter": "Particulate Nature of Matter",
    "chemical-combinations": "Chemical Combinations & Bonding",
    "properties-of-gases-gas-laws": "Gas Laws & Kinetic Theory",
    "acids-bases-and-salts": "Acids, Bases, and Salts",
    "periodic-table": "Periodic Table & Periodicity",
    "electrodes-electrochemical-series-and-electrolysis": "Electrochemistry & Electrolysis",
    "energy-and-chemical-reactions": "Chemical Energetics & Thermochemistry",
}


def slug_to_title(slug: str) -> str:
    if slug in TOPIC_NAME_OVERRIDES:
        return TOPIC_NAME_OVERRIDES[slug]
    words = slug.replace("-1", "").replace("-2", "").replace("-", " ").split()
    capitalized = []
    minor_words = {"and", "of", "in", "on", "at", "to", "for", "with", "a", "an", "the", "&"}
    for idx, w in enumerate(words):
        if w.lower() in minor_words and idx != 0:
            capitalized.append(w.lower())
        else:
            capitalized.append(w.capitalize())
    return " ".join(capitalized)


class Command(BaseCommand):
    help = "Seeds official curriculum topics for Mathematics, Physics, Chemistry, etc. from official_topics.json"

    def handle(self, *args, **options):
        json_path = Path("/home/kalmin/startups/myschool-past-questions-scraper/official_topics.json")
        if not json_path.exists():
            self.stdout.write(self.style.ERROR(f"Topic file not found: {json_path}"))
            return

        with open(json_path, "r", encoding="utf-8") as f:
            topics_data = json.load(f)

        subject_code_map = {
            "mathematics": ("Mathematics", "MATH", "math", "calculator"),
            "physics": ("Physics", "PHYS", "phys", "zap"),
            "chemistry": ("Chemistry", "CHEM", "chem", "flask-conical"),
            "biology": ("Biology", "BIO", "chem", "dna"),
            "english-language": ("English Language", "ENG", "math", "book-open"),
        }

        total_created = 0
        total_existing = 0

        for subj_slug, topics in topics_data.items():
            if subj_slug not in subject_code_map:
                continue
            name, code, theme, icon = subject_code_map[subj_slug]
            subject, _ = Subject.objects.get_or_create(
                slug=subj_slug,
                defaults={
                    "name": name,
                    "code": code,
                    "color_theme": theme,
                    "icon_name": icon,
                    "is_active": True,
                }
            )

            for order_idx, t_slug in enumerate(topics, start=1):
                t_name = slug_to_title(t_slug)
                topic, created = Topic.objects.get_or_create(
                    subject=subject,
                    slug=t_slug,
                    defaults={
                        "name": t_name,
                        "order": order_idx,
                        "description": f"Curriculum questions and revision modules on {t_name}.",
                    }
                )
                if created:
                    total_created += 1
                else:
                    total_existing += 1

            self.stdout.write(self.style.SUCCESS(f"Subject '{subject.name}': {len(topics)} topics mapped."))

        self.stdout.write(self.style.SUCCESS(f"Done! {total_created} topics created, {total_existing} already present."))
