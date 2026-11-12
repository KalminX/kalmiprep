"""
Canonical UTME/WAEC Topic Taxonomy & Multi-Field Weighted Question Classifier.

Provides:
1. CANONICAL_TOPICS: 14-18 ordered, mutually exclusive syllabus topics per subject.
2. Tier 1 Ground-Truth Scraper Lookup (from myschool_dataset/all_questions.jsonl).
3. Tier 2 Multi-Field Weighted Keyword, Formula & Rubric Scorer across
   question_text (x2.2), options (x1.4), and explanation (x1.2).
"""
import html
import json
import os
import re
from pathlib import Path

CANONICAL_TOPICS = {
    "chemistry": [
        {
            "slug": "matter-and-separation-techniques",
            "name": "Nature of Matter & Separation Techniques",
            "order": 1,
            "description": "Elements, compounds, mixtures, physical/chemical changes, purity criteria, and separation techniques.",
            "patterns": [
                (r"\b(filtration|distillation|fractional distillation|chromatography|sublimation|decantation|centrifugation|crystallization|recrystallization|separating funnel|sieving|evaporation to dryness|winnowing|magnetic separation|melting point determination|boiling point determination)\b", 10),
                (r"\b(physical change|chemical change|homogeneous mixture|heterogeneous mixture|pure substance|impure|miscible|immiscible|filtrate|residue|distillate|paper chromatography|adsorption|stationary phase|mobile phase)\b", 9),
                (r"\b(separation techniques?|separate a mixture|criteria of purity)\b", 8),
            ],
        },
        {
            "slug": "particulate-nature-of-matter",
            "name": "Particulate Nature of Matter, Laws & Formulae",
            "order": 2,
            "description": "Atoms, molecules, ions, Dalton's atomic theory, chemical laws of combination, valency, and chemical formulae.",
            "patterns": [
                (r"\b(dalton|law of conservation of mass|law of conservation of matter|definite proportions?|constant composition|multiple proportions?|reciprocal proportions?|matter can be converted into energy|e\s*=\s*mc)\b", 10),
                (r"\b(atomicity|polyatomic|diatomic|monoatomic|triatomic|valency|radical|chemical symbols?|relative atomic mass|relative molecular mass|vapour density)\b", 8),
            ],
        },
        {
            "slug": "atomic-structure-and-periodic-table",
            "name": "Atomic Structure, Orbitals & Nuclear Chemistry",
            "order": 3,
            "description": "Subatomic particles, atomic models, isotopes, quantum numbers, electronic configuration, and radioactivity.",
            "patterns": [
                (r"\b(radioactiv\w*|half[- ]life|nuclear fission|nuclear fusion|alpha particles?|beta particles?|gamma rays?|geiger|transmutation|binding energy|mass defect|radiocarbon|isotop\w*|isobars?|isotones?)\b", 10),
                (r"\b(hund'?s rule|pauli exclusion|aufbau|quantum numbers?|principal quantum|azimuthal|subsidiary quantum|magnetic quantum|spin quantum|s[- ]orbitals?|p[- ]orbitals?|d[- ]orbitals?|f[- ]orbitals?|electronic? configurations?|unpaired electrons?)\b", 10),
                (r"(1s2\s*2s2|2p6\s*3s2|1s\^?2|2p\^?[1-6]|3d\^?[1-9])", 10),
                (r"\b(rutherford|thomson|millikan|bohr|cathode rays?|oil drop|mass spectrometer|protons?|neutrons?|atomic number|mass number|nucleons?|subatomic)\b", 8),
                (r"(238\s*92\s*u|235\s*92\s*u|14\s*6\s*c|nuclear reaction|nuclear equation)", 10),
            ],
        },
        {
            "slug": "periodic-table",
            "name": "Periodic Table & Periodicity",
            "order": 4,
            "description": "Periodic law, groups and periods, and periodic trends in atomic radius, ionization energy, electron affinity, and electronegativity.",
            "patterns": [
                (r"\b(periodic law|periodic table|periodicity|ionization energ\w*|first ionization|electron affinity|electronegativity|atomic radi\w*|ionic radi\w*|diagonal relationship|metalloids?|actinides?|lanthanides?)\b", 10),
                (r"\b(group i\b|group ii\b|group iii\b|group iv\b|group v\b|group vi\b|group vii\b|group viii\b|group 0\b|period [1-7]\b|alkali metals?|alkaline earth|noble gas\w*|inert gas\w*|inert elements?|aerodrome beacons)\b", 8),
            ],
        },
        {
            "slug": "chemical-combinations",
            "name": "Chemical Bonding & Intermolecular Forces",
            "order": 5,
            "description": "Electrovalent, covalent, coordinate/dative, and metallic bonds; intermolecular forces, hybridization, and molecular geometry.",
            "patterns": [
                (r"\b(electrovalent|ionic bonds?|covalent bonds?|ionic compounds?|covalent compounds?|are ionic|are covalent|co-?ordinate bonds?|dative covalent|dative bonds?|metallic bonds?|hydrogen bonds?|van\s*der\s*waals|vander\s*waals|dipole[- ]dipole|london dispersion|intermolecular forces?|weakest attractive force)\b", 10),
                (r"\b(hybridization|sp3|sp2|sp\b|lone pairs?|bond pairs?|bond angles?|tetrahedral|trigonal planar|trigonal pyramidal|octahedral|linear shape|vsepr|shape of a? ?molecules?|octet rule|duplet)\b", 10),
                (r"\b(bond types?|kind of bonding|type of bond|bonding in)\b", 9),
            ],
        },
        {
            "slug": "stoichiometry-mole-concept",
            "name": "Stoichiometry, Mole Concept & Volumetric Analysis",
            "order": 6,
            "description": "Mole concept, Avogadro's constant, empirical/molecular formulae, reacting masses/volumes, molarity, and acid-base titrations.",
            "patterns": [
                (r"\b(empirical formula|molecular formula|percentage by mass|percentage composition|avogadro'?s?(?!\s+law)|molar mass|molar volume|22\.4\s*dm|6\.02\s*(?:x|\\times)\s*10|limiting reagent|stoichiometr\w*)\b", 10),
                (r"\b(molarity|molar concentration|concentration\s*\(mol|mol\s*dm|mass concentration|standard solution|primary standard|titration|burette|pipette|conical flask|titre|end[- ]point|equivalence point|volumetric analysis)\b", 9),
                (r"\b(how many moles|number of moles|calculate the mass|calculate the volume of gas|values of x,?\s*y|balance the (?:chemical )?(?:equation|reaction)|reacting mass)\b", 9),
            ],
        },
        {
            "slug": "properties-of-gases-gas-laws",
            "name": "Kinetic Theory of Matter & Gas Laws",
            "order": 7,
            "description": "States of matter, Brownian motion, Boyle's, Charles's, Graham's, Dalton's, Gay-Lussac's, Avogadro's, and ideal gas laws.",
            "patterns": [
                (r"\b(boyle'?s law|charles'? law|graham'?s law|dalton'?s law of partial pressure|gay[- ]lussac'?s law|avogadro'?s law|combined gas law|ideal gas|pv\s*=\s*nrt|rate of diffusion|effusion)\b", 10),
                (r"\b(kinetic theory|brownian motion|brownian movement|absolute zero|kelvin scale|s\.t\.p|standard temperature and pressure|partial pressure|equal volumes of different gases|volume occupied by .* at s\.t\.p|inflated balloon|gas molecules)\b", 9),
            ],
        },
        {
            "slug": "water-and-solubility-concept",
            "name": "Water, Solutions & Solubility",
            "order": 8,
            "description": "Water treatment, hard and soft water, solubility curves, true solutions, colloids, suspensions, efflorescence, deliquescence, and hygroscopy.",
            "patterns": [
                (r"\b(hard water|soft water|temporary hardness|permanent hardness|hardness of water|hardness in water|washing soda|permutit|ion[- ]exchange|zeolite|scum|lather with soap|boiler scale|stalactite|stalagmite)\b", 10),
                (r"\b(solubility|saturated solution|unsaturated solution|supersaturated|solubility curve|colloids?|suspensions?|emulsions?|aerosols?|tyndall effect|dialysis|coagulation|chlorination of water|water treatment)\b", 9),
                (r"\b(water of crystallization|efflorescen\w*|deliquescen\w*|hygroscop\w*|drying agents?|desiccants?|fused calcium chloride|silica gel)\b", 8),
            ],
        },
        {
            "slug": "air-and-air-pollution",
            "name": "Air & Environmental Chemistry",
            "order": 9,
            "description": "Composition of air, atmospheric pollutants, acid rain, ozone depletion, greenhouse effect, sewage, and biodegradable/non-biodegradable waste.",
            "patterns": [
                (r"\b(air pollutants?|water pollutants?|soil pollutants?|environmental pollution|acid rain|greenhouse effect|global warming|ozone layer|chlorofluorocarbons?|cfcs?|carbon\(ii\) oxide poisoning|carboxyhaemoglobin|smog|eutrophication|biodegradable|sewage|oil spillage|pollutants? found in the atmosphere|automobile exhaust)\b", 10),
                (r"\b(composition of air|constituents of air|noble gases in air|percentage of oxygen in air|percentage of nitrogen in air|alkaline pyrogallol|bubbled into alkaline)\b", 9),
            ],
        },
        {
            "slug": "acids-bases-and-salts",
            "name": "Acids, Bases, pH & Salts",
            "order": 10,
            "description": "Arrhenius, Bronsted-Lowry, and Lewis theories; pH, indicators, buffer solutions, neutralization, and preparation/hydrolysis of salts.",
            "patterns": [
                (r"\b(arrhenius|bronsted[- ]lowry|lewis acids?|lewis bases?|conjugate acids?|conjugate bases?|basicity of an acid|acid radicals?|acid anhydrides?|double decomposition|poh\b|ph scale|ph of|ph value|ph less than|ph greater than|hydrogen ion concentration|hydroxide ion|buffer solutions?)\b", 10),
                (r"\b(methyl orange|phenolphthalein|litmus|universal indicator|indicator most suitable|neutralization|acid salts?|normal salts?|double salts?|complex salts?|basic salts?|hydrolysis of salts?|weak acids?|strong acids?|weak bases?|strong bases?|hydrohalic acids?|amphoteric|solution is acidic|aqueous solution of .* is acidic|aqueous solution of .* is basic|aqueous solution of .* is neutral)\b", 10),
                (r"\b(2nahco3|baking soda|epsom salt|slaked lime|quicklime|caustic soda|caustic potash|milk of magnesia|dissolve marble)\b", 7),
            ],
        },
        {
            "slug": "electrochemistry-and-redox",
            "name": "Oxidation, Reduction & Redox Reactions",
            "order": 11,
            "description": "Oxidation numbers, oxidizing and reducing agents, half-equations, and redox tests.",
            "patterns": [
                (r"\b(oxidation numbers?|oxidation states?|oxidizing agents?|reducing agents?|redox|half[- ]equations?|half[- ]reactions?|disproportionation|hexacyanoferrate|tetraoxomanganate|dichromate|heptaoxodichromate|bleaches by|reducing properties of)\b", 10),
                (r"(cr2o7|mno4|\+\s*[nx]e-|\+\s*\d+e-|\[fe\(cn\))", 10),
            ],
        },
        {
            "slug": "electrodes-electrochemical-series-and-electrolysis",
            "name": "Electrolysis & Electrochemical Cells",
            "order": 12,
            "description": "Electrolytes, electrochemical series, preferential discharge, Faraday's laws of electrolysis, electrode potentials, and galvanic cells.",
            "patterns": [
                (r"\b(electrolysis|electrolytes?|non[- ]electrolytes?|faraday|96500|coulombs?|electrochemical series|preferential discharge|anode|cathode|electrolytic cells?|electrochemical cells?|galvanic cells?|voltaic cells?|daniell? cell|leclanche|lead[- ]acid accumulator)\b", 10),
                (r"\b(standard electrode potentials?|electrode potentials?|salt bridge|electroplating|anodizing|deposit\s+[0-9.]+g|passing a current of|quantity of electricity|amperes? for|displace copper from|zinc rod is immersed in copper|strip of iron is placed in .* cuso4|blue colou?r of the .* solution (?:fades|disappears))\b", 10),
            ],
        },
        {
            "slug": "energy-and-chemical-reactions",
            "name": "Chemical Energetics & Thermochemistry",
            "order": 13,
            "description": "Exothermic and endothermic reactions, enthalpy changes, Hess's law, entropy, Gibbs free energy, and spontaneity.",
            "patterns": [
                (r"\b(exothermic|endothermic|enthalpy|heat of reaction|heat of neutralization|heat of combustion|heat of formation|heat of solution|hess'?s law|bond energy|lattice energy|hydration energy)\b", 10),
                (r"\b(entropy|gibbs free energy|spontaneity|spontaneous reaction|non[- ]spontaneous|\\delta\s*h|\\delta\s*g|\\delta\s*s|Δh|Δg|Δs|energy profile)\b", 10),
            ],
        },
        {
            "slug": "kinetics-energetics-and-equilibrium",
            "name": "Reaction Rates & Chemical Equilibrium",
            "order": 14,
            "description": "Factors affecting reaction rates, collision theory, activation energy, reversible reactions, equilibrium constants, and Le Chatelier's principle.",
            "patterns": [
                (r"\b(le chatelier|chemical equilibrium|dynamic equilibrium|system at equilibrium|reaction at equilibrium|equilibrium constant|equilibrium position|k_c\b|k_p\b|law of mass action|reversible reaction)\b", 10),
                (r"(⇌|\\rightleftharpoons|<=>)", 10),
                (r"\b(rate of reaction|rate of a? ?chemical reaction|reaction rate|collision theory|effective collisions?|surface area of reactants?|arrhenius law|order of reaction|rate law|rate curve|if a catalyst is added|activation energy)\b", 10),
            ],
        },
        {
            "slug": "non-metals-and-their-compounds",
            "name": "Non-Metals & Their Compounds",
            "order": 15,
            "description": "Hydrogen, oxygen, carbon allotropes, nitrogen/ammonia (Haber), sulphur/H2SO4 (Contact), and halogens.",
            "patterns": [
                (r"\b(haber process|contact process|ostwald process|frasch process|bosch process|solvay process|fountain experiment|kipps? apparatus|laboratory preparation of ammonia|preparation of chlorine|preparation of hydrogen|preparation of oxygen|preparation of sulphur|ammonia is produced on an industrial)\b", 10),
                (r"\b(allotrop\w*|diamond|graphite|fullerene|coal|coke|producer gas|water gas|coal gas|lime\s*water milky|turns lime\s*water|nitrogenous|ammonium trioxonitrate|sulphur\s*\(iv\)|sulphur\s*\(vi\)|hydrogen sulphide|bleaching action of chlorine|bleaching powder|chlorine and iodine at room temperature|bubbling chlorine through|react with steam at red heat)\b", 9),
            ],
        },
        {
            "slug": "metals-and-their-compounds-1",
            "name": "Metals, Transition Elements & Extraction",
            "order": 16,
            "description": "Alkali/alkaline earth metals, aluminium, iron, copper, tin, zinc, extraction of metals, alloys, corrosion, and transition metal properties.",
            "patterns": [
                (r"\b(blast furnace|hall[- ]heroult|bauxite|cryolite|haematite|magnetite|siderite|cassiterite|galena|zinc blende|ores? of iron|ores? of aluminium|ores? of copper|ores? of tin|froth flotation|roasting of ore|smelting|slag|pig iron|cast iron|wrought iron|main function of limestone)\b", 10),
                (r"\b(duralumin|brass|bronze|stainless steel|solder|type metal|permalloy|alnico|alloys?|transition metals?|noble metals?|lustre of a metal|coloured nature of transition|paramagnet\w*|variable oxidation|rust|rusting|galvaniz\w*|sacrificial protection|high reactivity of sodium|stored under paraffin|stored under kerosene|flame test|colour of the flame|brick[- ]red|lilac flame|green precipitate|reddish[- ]brown precipitate|white precipitate .* redissolves|excess alkali)\b", 10),
                (r"\b(differences in the chemical properties of metals and non-metals|reactivity series|thermite)\b", 9),
            ],
        },
        {
            "slug": "hydrocarbons",
            "name": "Organic Chemistry I: Hydrocarbons & Crude Oil",
            "order": 17,
            "description": "Homologous series, IUPAC nomenclature, isomerism, alkanes, alkenes, alkynes, benzene, and petroleum refining/cracking.",
            "patterns": [
                (r"\b(homologous series|alkanes?|alkenes?|alkynes?|alkyl group|cyclohexane|benzene|aromatic hydrocarbons?|aliphatic|saturated hydrocarbons?|unsaturated hydrocarbons?|c_nh_2n|methylbutane|methylpropane|dichloroethene)\b", 10),
                (r"\b(isomers?|isomerism|structural isomers?|geometric isomers?|cis[- ]trans|chiral|optical isomers?|octane number|octane rating|anti[- ]knock|tetraethyl lead|cracking|reforming|crude oil|petroleum|bitumen|kerosene fraction|natural gas|marsh gas|calcium carbide|calcium ethynide|acetylene|oxy-acetylene|oxy-ethylene|ethyne|ethene|methane|butane|propane|pentane|hexane)\b", 10),
                (r"\b(markovnikov|ozonolysis|baeyer|decolorizes bromine water|bromine water|ammoniacal copper\(i\)|ammoniacal silver|tollens)\b", 10),
            ],
        },
        {
            "slug": "organic-chemistry",
            "name": "Organic Chemistry II: Functional Groups, Polymers & Biomolecules",
            "order": 18,
            "description": "Alkanols, alkanals, alkanones, alkanoic acids, alkanoates, soaps/detergents, carbohydrates, proteins, polymers, and chemical industries.",
            "patterns": [
                (r"\b(alkanols?|secondary alkanols?|primary alkanols?|tertiary alkanols?|alcohols?|ethanol|methanol|propan-[12]-ol|butan-[12]-ol|alkanals?|aldehydes?|alkanones?|ketones?|alkanoic acids?|carboxylic|ethanoic acid|alkanoates?|esters?|esterification|saponification|boiling of fat|soaps?|detergents?|fats?|hydrogenation of oil|margarine|palm wine)\b", 10),
                (r"\b(iodoform test|lucas test|fehling'?s solution|benedict'?s solution|biuret test|millon'?s reagent|xanthoproteic|sudan iii|fermentation|zymase|diastase|invertase|maltase|monosaccharides?|disaccharides?|polysaccharides?|glucose|fructose|sucrose|starch|cellulose|proteins?|amino acids?|peptides?|enzymes?|amines?|amides?|nylon|terylene|bakelite|perspex|vulcanization|natural rubber|synthetic polymers?|polymerization|siting a chemical industry|chemical industr\w*)\b", 10),
                (r"\b(functional groups?|hydroxyl|carboxyl|carbonyl|ch3ch)\b", 9),
            ],
        },
    ],
    "mathematics": [
        {
            "slug": "number-bases",
            "name": "Number Bases & Modular Arithmetic",
            "order": 1,
            "description": "Conversion between number bases, arithmetic in different bases, and modular arithmetic.",
            "patterns": [
                (r"(_\{\\text\{(two|three|four|five|six|seven|eight|nine)\}\}|base\s+[2-9]|base\s+10|base\s+ten|base\s+two|base\s+three|base\s+four|base\s+five|base\s+six|base\s+seven|base\s+eight|binary number|octal|hexadecimal|mod\s*\d+|modulo|modular arithmetic|\(\\text\{mod\}\s*\d+\))", 10),
            ],
        },
        {
            "slug": "fractions-decimals-percentages-and-approximation",
            "name": "Fractions, Decimals, Percentages & Approximations",
            "order": 2,
            "description": "Fractions, decimals, significant figures, standard form, ratios, rates, percentages, profit/loss, and simple/compound interest.",
            "patterns": [
                (r"\b(significant figures?|decimal places?|nearest whole number|nearest tenth|nearest hundredth|nearest thousand|percentage error|relative error|standard form|scientific notation|simple interest|compound interest|depreciation|profit|loss|cost price|selling price|discount|commission|value added tax|vat|income tax|ratios?|proportions?|rate of|bodmas|ascending order of magnitude|descending order of magnitude|numerator and denominator|place value|value of \d in the number)\b", 10),
                (r"(\d+\s*%|per\s*cent|naira|₦|n\d+\.00|\$[0-9,]+)", 7),
            ],
        },
        {
            "slug": "indices-logarithms-and-surds",
            "name": "Indices, Logarithms & Surds",
            "order": 3,
            "description": "Laws of indices, exponential equations, logarithms, rationalization of surds, and conjugate surds.",
            "patterns": [
                (r"(\\log|\d*log\b|log_\{?\d*\}?|logarithms?|antilog|mantissa|characteristic|surds?|rationalize|conjugate|\\sqrt\{\d+\})", 10),
                (r"(\d+\^\{?[xyn23456789-]+|\d+\\\(\\?\^[{\d&\\-]+|[2345789]\^\{?[2345xyn-]+\}?\s*=|\bindices\b|\bindex\b)", 7),
            ],
        },
        {
            "slug": "sets",
            "name": "Sets, Logic & Venn Diagrams",
            "order": 4,
            "description": "Set notation, union, intersection, complement, power sets, 2- and 3-set Venn diagram problems, and mathematical logic.",
            "patterns": [
                (r"(\\cup|\\cap|\\subset|\\emptyset|∪|∩|⊂|⊆|∈|∉|universal set|venn diagram|complement of a set|disjoint sets?|power set|subsets?|n\(a\s*\\cup|n\(p\s*\\cup|truth table|logical statement|contrapositive|converse|inverse of the statement|tautology|implication)", 10),
                (r"\b(play football|speak hausa|speak yoruba|speak igbo|offer biology|offer chemistry|offer physics|study french|study history|both subjects|neither of them)\b", 8),
            ],
        },
        {
            "slug": "polynomials",
            "name": "Algebraic Expressions, Polynomials & Factorisation",
            "order": 5,
            "description": "Expansion, factorisation, algebraic fractions, change of subject of formula, remainder theorem, and factor theorem.",
            "patterns": [
                (r"\b(polynomials?|remainder theorem|factor theorem|when .* is divided by|divisible by\s+x\s*[+-]|factori[sz]e completely|factori[sz]e|difference of two squares|algebraic fractions?|partial fractions?|make .* the subjects? of the formula|subject of the relation|subject of the formula|is undefined|undefined when|expand\b|coefficient of x)\b", 10),
                (r"\(\d+\.\d+\)\^?2\s*-\s*\(\d+\.\d+\)\^?2", 9),
            ],
        },
        {
            "slug": "quadratic-equations",
            "name": "Linear, Simultaneous & Quadratic Equations",
            "order": 6,
            "description": "Linear equations, simultaneous equations, quadratic equations, sum and product of roots, and word problems.",
            "patterns": [
                (r"\b(quadratic equations?|quadratic expressions?|perfect square|completing the square|discriminant|equal roots|real roots|roots of the equation|sum of roots|product of roots|simultaneous equations?|solve for x and y|solve the equations?|constant speed|average speed|one-third of his money)\b", 9),
                (r"(\\alpha\b|\\beta\b|1/\\alpha|x\^2\s*[+-]\s*\d*x|\dx2\s*[+-]\s*\dx|x\\\(\^2\\\)?\s*[+-])", 9),
            ],
        },
        {
            "slug": "linear-inequalities",
            "name": "Inequalities & Linear Programming",
            "order": 7,
            "description": "Linear and quadratic inequalities in one or two variables, number lines, and shaded graphical regions.",
            "patterns": [
                (r"(\\le\b|\\ge\b|\\leq\b|\\geq\b|≤|≥|\binequalit\w*|range of values of x|satisfy the inequality|satisfy the equation .* <\s*x|1\s*<\s*x|shaded region|number line|linear programming)", 10),
            ],
        },
        {
            "slug": "variations",
            "name": "Variations",
            "order": 8,
            "description": "Direct, inverse, joint, and partial variations.",
            "patterns": [
                (r"\b(varies directly|varies inversely|varies jointly|joint variation|partial variation|partly constant and partly varies|directly proportional|inversely proportional|\\propto|∝)\b", 10),
            ],
        },
        {
            "slug": "progressions",
            "name": "Sequences & Series (AP & GP)",
            "order": 9,
            "description": "Arithmetic progressions (AP), geometric progressions (GP), nth terms, sum of n terms, and sum to infinity.",
            "patterns": [
                (r"\b(arithmetic progression|geometric progression|a\.p\.?\b|g\.p\.?\b|common difference|common ratio|sum to infinity|s_\\infty|nth term|n\^\{?th\}? term|first term and common|sequence|series)\b", 10),
            ],
        },
        {
            "slug": "matrices-and-determinants",
            "name": "Binary Operations, Matrices & Determinants",
            "order": 10,
            "description": "Binary operations, identity and inverse elements, matrix algebra, determinants, and inverse of 2x2 and 3x3 matrices.",
            "patterns": [
                (r"\b(matrix|matrices|determinants?|transpose|adjoint|inverse of the matrix|singular matrix|\\begin\{pmatrix\}|\\begin\{bmatrix\}|\\begin\{vmatrix\}|binary operation|identity element|inverse of .* under the operation|commutative|associative|defined on the set of real numbers by)\b", 10),
                (r"(\ba\s*\*\s*b\s*=|\bx\s*\*\s*y\s*=|\bp\s*\*\s*q\s*=|\bm\s*\*\s*n\s*=|\\ast|\bvalue of \d+\s*\*\s*\d+)", 10),
            ],
        },
        {
            "slug": "circles",
            "name": "Plane Geometry, Polygons & Circle Theorems",
            "order": 11,
            "description": "Angles on parallel lines, triangles, congruence, similarity, interior/exterior angles of polygons, circle theorems, constructions, and loci.",
            "patterns": [
                (r"\b(circle theorems?|is a circle|cyclic quadrilateral|centre of the circle|chord|tangent to a circle|angle at the centre|angle in a semicircle|alternate segment|inscribed circle|circumscribed|interior angles?|exterior angles?|angles of a polygon|regular polygon|quadrilateral|pentagon|hexagon|heptagon|octagon|nonagon|decagon|parallelogram|rhombus|diagonal|trapezium|kite|isosceles triangle|equilateral triangle|similar triangles?|congruent|bisector|constructed an angle|locus|loci|equidistant|parallel to|parallel lines|transversal|alternative angles|alternate angles|corresponding angles|vertically opposite|supplementary|complementary|in the figure,?\s*p[qs]|&ang;[a-z]{3})\b", 10),
            ],
        },
        {
            "slug": "mensuration",
            "name": "Mensuration (Areas, Perimeters & Volumes)",
            "order": 12,
            "description": "Lengths of arcs, perimeters, areas of plane shapes/sectors/segments, surface areas and volumes of solids, and latitude/longitude.",
            "patterns": [
                (r"\b(total surface area|curved surface area|surface area|volume of a|volume of the|cylinder|cone|sphere|hemisphere|pyramid|prism|frustum|cuboid|cube|sector of a circle|length of an arc|area of a sector|area of a semi-circle|area of a circle|area of (?:the |a )?triangle|area of (?:the |a )?trapezium|area of (?:the |a )?parallelogram|segment of a circle|perimeter of|circumference|radius of .* cm|diameter\s+\d+|latitude|longitude|great circle|small circle|nautical mile)\b", 10),
            ],
        },
        {
            "slug": "coordinate-geometry-of-straight-lines",
            "name": "Coordinate Geometry",
            "order": 13,
            "description": "Distance between points, midpoint, gradient, equation of a straight line, and parallel and perpendicular lines.",
            "patterns": [
                (r"\b(gradient of|y[- ]intercept|x[- ]intercept|slope[- ]intercept|midpoint|coordinates of|distance between the points|collinear|perpendicular to the line|parallel to the line|equation of the line|equation of a straight line|passes through the points?)\b", 10),
            ],
        },
        {
            "slug": "trigonometric-ratios",
            "name": "Trigonometry, Elevation & Bearings",
            "order": 14,
            "description": "Sine, cosine, and tangent ratios, special angles, sine and cosine rules, angles of elevation and depression, and bearings.",
            "patterns": [
                (r"\b(angles? of elevation|angles? of depression|bearing of|three[- ]figure bearing|compass bearing|north of east|south of east|north of west|south of west|resultant of the two forces|sine rule|cosine rule|quadrant|acute angle|trigonometric)\b", 12),
                (r"(\\sin\b|\\cos\b|\\tan\b|\\sec\b|\\csc\b|\\cot\b|\bsin\s*\\?theta|\bcos\s*\\?theta|\btan\s*\\?theta|sinθ|cosθ|tanθ|\\?tan\s*\d+|\\?sin\s*\d+|\\?cos\s*\d+)", 12),
            ],
        },
        {
            "slug": "differentiation",
            "name": "Differentiation & Applications",
            "order": 15,
            "description": "Limits, derivatives of algebraic and trigonometric functions, chain/product/quotient rules, tangents, normals, rates of change, and maxima/minima.",
            "patterns": [
                (r"(\\frac\{dy\}\{dx\}|dy/dx|differentiate|derivative|first principle|gradient of the curve|tangent to the curve|normal to the curve|stationary point|turning point|maximum value|minimum value|maxima|minima|point of inflexion|rate of change|\\lim_)", 18),
            ],
        },
        {
            "slug": "integration",
            "name": "Integration & Applications",
            "order": 16,
            "description": "Indefinite and definite integrals, area under a curve, and volume of revolution.",
            "patterns": [
                (r"(\\int|∫|\bintegrate\b|\bintegration\b|\bintegral\b|area bounded by the curve|area under the curve|volume of revolution)", 18),
            ],
        },
        {
            "slug": "statistics",
            "name": "Statistics (Data Representation, Central Tendency & Dispersion)",
            "order": 17,
            "description": "Bar charts, pie charts, histograms, cumulative frequency (ogive), mean, median, mode, range, mean deviation, variance, and standard deviation.",
            "patterns": [
                (r"\b(mean deviation|standard deviation|variance|interquartile range|semi[- ]interquartile|quartile|percentile|decile|cumulative frequency|ogive|histogram|pie chart|bar chart|frequency distribution|frequency table|frequency\b|arithmetic mean|find the mean|calculate the mean|mean of|mean score|mean age|average age|median|modal|mode of|find the mode)\b", 10),
                (r"(&sum;f|\\sum\s*x|\\sum\s*f|\\overline\{x\}|took the examination)", 9),
            ],
        },
        {
            "slug": "probability",
            "name": "Permutations, Combinations & Probability",
            "order": 18,
            "description": "Factorials, permutations, combinations, experimental and theoretical probability, addition and multiplication laws of probability.",
            "patterns": [
                (r"\b(probability|thrown|tossed|fair die|two dice|fair coin|pack of cards|playing cards|balls in a bag|mutually exclusive|independent events|with replacement|without replacement|permutations?|combinations?|how many ways|how many possible ways|arranged|committees? of|seated at a circular|factorial)\b", 10),
                (r"(\(n\s*-\s*1\)!|\\binom|\^\{\d+\}c_\d+)", 10),
            ],
        },
    ],
    "physics": [
        {
            "slug": "measurement",
            "name": "Units, Measurements & Dimensional Analysis",
            "order": 1,
            "description": "Fundamental and derived quantities/units, dimensional analysis, vernier calipers, micrometer screw gauge, and balances.",
            "patterns": [
                (r"\b(fundamental quantit\w*|derived quantit\w*|fundamental units?|derived units?|s\.i\.? units?|dimensional analysis|dimensions? of|vernier call?ipers?|micrometer screw gauge|beam balance|spring balance|stop\s*watch)\b", 10),
                (r"(mlt\^|m\^?[0-9-]*l\^?[0-9-]*t\^?[0-9-]*)", 9),
            ],
        },
        {
            "slug": "scalars-and-vectors",
            "name": "Scalars, Vectors & Relative Motion",
            "order": 2,
            "description": "Scalar and vector quantities, resultant of vectors, resolution of vectors, and relative velocity.",
            "patterns": [
                (r"\b(scalar quantit\w*|vector quantit\w*|is a vector|is a scalar|scalars? and vectors?|equal vectors|two vectors|resultant force|resultant velocity|resultant r? ?of two|parallelogram law of vectors?|triangular law|vertical component|horizontal component|resolved along|relative velocity|relative motion|travelling in opposite directions)\b", 10),
            ],
        },
        {
            "slug": "linear-motion",
            "name": "Linear Motion, Projectiles & Kinematics",
            "order": 3,
            "description": "Speed, velocity, acceleration, equations of uniformly accelerated motion, motion graphs, free fall, and projectile motion.",
            "patterns": [
                (r"\b(accelerates? from rest|uniform acceleration|retardation|deceleration|velocity[- ]time graph|displacement[- ]time graph|equations? of motion|moving on a straight|free fall|dropped from a height|thrown vertically|projected horizontally|projectiles?|time of flight|maximum height|horizontal range|trajectory)\b", 10),
                (r"(v\s*=\s*u\s*\+\s*at|s\s*=\s*ut|x\s*=\s*ut|v\^2\s*=\s*u\^2|\\frac\{2h\}\{g\})", 9),
            ],
        },
        {
            "slug": "momentum-impulse-newtons-law-of-motion",
            "name": "Newton's Laws, Momentum & Collisions",
            "order": 4,
            "description": "Inertia, Newton's laws of motion, impulse, conservation of linear momentum, elastic/inelastic collisions, and friction.",
            "patterns": [
                (r"\b(newton'?s (?:first|second|third) law|law of inertia|linear momentum|conservation of linear momentum|impulse|elastic collision|inelastic collision|recoil velocity|coeff?icient of (?:static|dynamic|kinetic|limiting)? ?friction|frictional force|limiting friction|reduce friction|lubricants?|normal reaction|impart to them,?\s*acceleration|masses in the ratio)\b", 10),
            ],
        },
        {
            "slug": "equilibrium-of-forces-1",
            "name": "Equilibrium of Forces, Moments & Flotation",
            "order": 5,
            "description": "Moment of a force, principle of moments, couples, centre of gravity, stability, Archimedes' principle, and law of flotation.",
            "patterns": [
                (r"\b(moment of a force|principle of moments|clockwise moment|anticlockwise moment|centre of gravity|center of gravity|couple|torque|stable equilibrium|unstable equilibrium|neutral equilibrium|uniform metre rule|pivoted|knife[- ]edge|archimedes'? principle|law of flotation|upthrust|apparent weight|relative density|density of water|hydrometer)\b", 10),
            ],
        },
        {
            "slug": "work-energy-power",
            "name": "Work, Energy, Power & Simple Machines",
            "order": 6,
            "description": "Work, kinetic and potential energy, conservation of mechanical energy, power, and simple machines (M.A., V.R., efficiency).",
            "patterns": [
                (r"\b(mechanical advantage|velocity ratio|m\.a\b|v\.r\b|efficiency of|simple machines?|block and tackle|pulley system|inclined plane|plane inclined at|wheel and axle|screw jack|hydraulic press|lever|fulcrum|load and effort|kinetic energy|potential energy|work done|power developed)\b", 10),
            ],
        },
        {
            "slug": "simple-harmonic-motion-1",
            "name": "Circular Motion, Gravitation & Simple Harmonic Motion",
            "order": 7,
            "description": "Angular velocity, centripetal/centrifugal force, Newton's law of gravitation, satellites, escape velocity, and simple harmonic motion.",
            "patterns": [
                (r"\b(simple harmonic motion|s\.h\.m|simple pendulum|period of oscillation|angular velocity|angular frequency|centripetal|centrifugal|banked road|conical pendulum|gravitational field|gravitational pull|gravitational force|newton'?s law of universal gravitation|escape velocity|parking orbit|geostationary|satellite|artificial satellite|kepler)\b", 10),
            ],
        },
        {
            "slug": "deformation-of-solids",
            "name": "Elasticity, Density, Pressure & Fluids",
            "order": 8,
            "description": "Hooke's law, Young's modulus, elastic potential energy, pressure in fluids, Pascal's principle, surface tension, capillarity, and viscosity.",
            "patterns": [
                (r"\b(hooke'?s law|elastic limit|yield point|young'?s modulus|tensile stress|tensile strain|force constant|energy stored in a stretched|spiral spring|stretches a spring|stretches the spring|extension of|surface tension|capillarity|meniscus|angle of contact|viscosity|terminal velocity|stokes'? law|barometer|manometer|atmospheric pressure|pascal'?s principle|hare'?s apparatus)\b", 10),
            ],
        },
        {
            "slug": "heat-and-temperature",
            "name": "Temperature, Thermometry & Thermal Expansion",
            "order": 9,
            "description": "Temperature scales, thermometers, fixed points, linear/area/cubic expansivity, and anomalous expansion of water.",
            "patterns": [
                (r"\b(thermometers?|measure the temperature|upper fixed point|lower fixed point|ice point|steam point|kelvin temperature|celsius|fahrenheit|thermocouple|platinum resistance|clinical thermometer|pyrometer|linear expansivity|area expansivity|superficial expansivity|cubic expansivity|volume expansivity|apparent expansivity|expansivity of|anomalous expansion of water|bimetallic strip)\b", 10),
            ],
        },
        {
            "slug": "heat-energy",
            "name": "Calorimetry, Latent Heat & Change of State",
            "order": 10,
            "description": "Specific heat capacity, calorimetry, specific latent heat of fusion and vaporization, evaporation, boiling, vapour pressure, and relative humidity.",
            "patterns": [
                (r"\b(specific heat capacity|thermal capacity|heat capacity|calorimeter|method of mixtures|latent heat|specific latent heat of fusion|specific latent heat of vapou?rization|evaporation|boiling point|melting point|regelation|saturated vapour pressure|dew point|relative humidity|hygrometer|wet and dry bulb|refrigerator)\b", 10),
            ],
        },
        {
            "slug": "thermodynamics",
            "name": "Gas Laws & Heat Transfer",
            "order": 11,
            "description": "Boyle's, Charles's, and pressure laws; kinetic theory of gases; conduction, convection, radiation, and thermos flask.",
            "patterns": [
                (r"\b(boyle'?s law|charles'? law|pressure law|general gas law|ideal gas|given mass of a gas|volume of a gas|for a gas|kinetic theory of gases|root mean square|conduction|thermal conductivity|convection|land and sea breeze|radiation|black body|thermos flask|vacuum flask)\b", 10),
            ],
        },
        {
            "slug": "waves-1",
            "name": "Waves, Sound & Vibrations",
            "order": 12,
            "description": "Wave properties, wave equation, interference, diffraction, polarization, sound waves, echoes, resonance, harmonics in strings and pipes.",
            "patterns": [
                (r"\b(transverse waves?|longitudinal waves?|mechanical waves?|progressive waves?|stationary waves?|standing waves?|wave in a plucked|crests? of a wave|\bcrest\b|troughs?|nodes?|antinodes?|wavelength|amplitude|phase difference|wave equation|interference|diffraction|polarization|echo|reverberation|ultrasonic|mach number|sonometer|resonance tube|closed pipe|open pipe|stringed instrument|wind instrument|percussion|overtones?|harmonics?|fundamental frequency|beat frequency|doppler effect)\b", 10),
                (r"\\frac\{v\}\{\\lambda\}", 10),
            ],
        },
        {
            "slug": "reflection-of-light",
            "name": "Reflection, Refraction & Dispersion of Light",
            "order": 13,
            "description": "Plane and curved mirrors, mirror formula, Snell's law, refractive index, total internal reflection, prisms, dispersion, colours, and EM spectrum.",
            "patterns": [
                (r"\b(plane mirrors?|concave mirrors?|convex mirrors?|parabolic mirrors?|radius of curvature|principal focus|mirror formula|pinhole camera|periscope|kaleidoscope|refraction|snell'?s law|refractive index|glass block|real depth|apparent depth|views the object vertically|lateral displacement|critical angle|total internal reflection|mirage|optical fibre|triangular prism|angle of minimum deviation|dispersion of white light|monochromatic|primary colou?rs?|secondary colou?rs?|complementary colou?rs?|electromagnetic spectrum)\b", 10),
            ],
        },
        {
            "slug": "application-of-lens",
            "name": "Lenses & Optical Instruments",
            "order": 14,
            "description": "Converging and diverging lenses, lens formula, cameras, projectors, microscopes, telescopes, and the human eye/defects of vision.",
            "patterns": [
                (r"\b(converging lens|diverging lens|four lenses|biconvex|biconcave|focal length|power of a lens|dioptre|linear magnification|microscope objective|compound microscope|simple microscope|magnifying glass|astronomical telescope|terrestrial telescope|helioscope|slide projector|human eye|myopia|short[- ]sighted\w*|hypermetropia|long[- ]sighted\w*|astigmatism|presbyopia|accommodation|retina|cornea|ciliary)\b", 10),
            ],
        },
        {
            "slug": "electric-field-1",
            "name": "Electrostatics & Capacitors",
            "order": 15,
            "description": "Electric charges, electroscope, Coulomb's law, electric field intensity, electric potential, capacitance, and series/parallel capacitors.",
            "patterns": [
                (r"\b(electrostatics?|coulomb'?s law|electroscope|electrophorus|lightning conductor|point discharge|electric field|charged particles?|two charges|carrying a charge of|electric force|electric potential|permittivity|capacitance|capacitors?|microfarad|farad|dielectric|parallel plate)\b", 10),
                (r"4\s*\\pi\s*\\mathit\{e\}_o|\\varepsilon_0", 10),
            ],
        },
        {
            "slug": "current-electricity-1",
            "name": "Current Electricity & Electric Circuits",
            "order": 16,
            "description": "Ohm's law, resistance, resistivity, series/parallel circuits, EMF and internal resistance, potentiometer, metre bridge, and electrical energy/power.",
            "patterns": [
                (r"\b(ohm'?s law|electromotive force|e\.?m\.?f|potential difference|open circuit|closed circuit|internal resistance|terminal potential|lost volt|electrical resistance|electric heater of resistance|resistivity|conductivity|shunt|multiplier|galvanometer|ammeter|voltmeter|potentiometer|wheatstone bridge|metre bridge|rheostat|resistors? in series|resistors? in parallel|kirchhoff|electric power|fuse|kilowatt[- ]hour|kwh|daniell cell|leclanche|lead[- ]acid)\b", 10),
            ],
        },
        {
            "slug": "magnetic-field-1",
            "name": "Magnetism, Electromagnetism & AC Circuits",
            "order": 17,
            "description": "Magnets, Earth's magnetic field, force on current-carrying conductor, electromagnetic induction (Faraday/Lenz), transformers, and RLC AC circuits.",
            "patterns": [
                (r"\b(magnetic field|combined electric and magnetic|parallel wires carry currents|magnetic flux|magnetic meridian|angle of declination|angle of dip|inclination|paramagnetic|diamagnetic|ferromagnetic|curie point|solenoid|electromagnet|magnet is being inserted|induced e\.?m\.?f|coil of wire|fleming'?s (?:left|right)[- ]hand rule|faraday'?s law of electromagnetic|lenz'?s law|eddy current|inductance|inductor|henry|transformer|electric generator|step[- ]up|step[- ]down|dynamo|alternator|d\.c\.? motor|moving[- ]coil|alternating current|a\.c\.? circuit|r\.m\.s|peak voltage|capacitive reactance|inductive reactance|impedance|resonance frequency|power factor)\b", 11),
            ],
        },
        {
            "slug": "modern-physics-and-nuclear-physics",
            "name": "Atomic, Quantum, Nuclear Physics & Electronics",
            "order": 18,
            "description": "Atomic energy levels, photoelectric effect, thermionic emission, X-rays, radioactivity, half-life, nuclear energy, and semiconductors/logic gates.",
            "patterns": [
                (r"\b(elementary modern physics|quantum mechanics|special relativity|photoelectric effect|work function|threshold frequency|threshold wavelength|stopping potential|planck'?s constant|photon|einstein'?s photoelectric|thermionic emission|cathode ray oscilloscope|cathode rays?|conduction of electricity through gases|discharge tube|x[- ]rays?|wave[- ]particle duality|de broglie|heisenberg uncertainty|energy level|excitation|ionization potential|radioactiv\w*|half[- ]life|half of \d+ min|count rate|decay constant|alpha|beta|gamma|nuclear fission|nuclear fusion|binding energy|mass defect|semiconductors?|intrinsic|extrinsic|p[- ]type|n[- ]type|p[- ]n junction|diode|rectification|transistor|logic gate)\b", 11),
            ],
        },
    ],
    "biology": [
        {
            "slug": "classification-or-organisation-of-life",
            "name": "Variety of Organisms & Classification of Living Things",
            "order": 1,
            "description": "Characteristics of living things, binomial nomenclature, kingdoms Monera, Protista, Fungi, Plantae, and Animalia, and viruses.",
            "patterns": [
                (r"\b(taxonomy|binomial nomenclature|carolus linnaeus|species are groups of organisms|interbreed and produce fertile|kingdom monera|protista|protozoa|fungi|plantae|animalia|phylum|coelenterata|cnidaria|platyhelminthes|nematoda|annelida|mollusca|arthropoda|crustacea|insecta|arachnida|myriapoda|echinodermata|chordata|pisces|amphibia|reptilia|aves|mammalia)\b", 10),
                (r"\b(algae|thallophyta|bryophyt\w*|pteridophyt\w*|spermatophyt\w*|gymnosperm\w*|angiosperm\w*|monocot\w*|dicot\w*|liverwort|moss|fern|spirogyra|amoeba|paramecium|euglena|chlamydomonas|hydra|tapeworm|earthworm|cockroach|tilapia|toad|agama|virus\w*|bacteriophage)\b", 9),
            ],
        },
        {
            "slug": "cell-1-living-unit-structure",
            "name": "Cell Structure, Organization & Cell Division",
            "order": 2,
            "description": "Plant and animal cells, organelles and functions, levels of organization (cell, tissue, organ, system), mitosis, and meiosis.",
            "patterns": [
                (r"\b(organelles?|mitochondri\w*|chloroplasts?|ribosomes?|golgi|endoplasmic reticulum|lysosomes?|vacuoles?|centrioles?|cell wall|cell membrane|plasma membrane|nucleus|nucleolus|chromatin|prokaryot\w*|eukaryot\w*|example\s+of a tissue|similar structure and function|robert hooke|schleiden|schwann)\b", 10),
                (r"\b(mitosis|meiosis|prophase|metaphase|anaphase|telophase|interphase|cytokinesis|spindle fibres?|chromatids?|homologous chromosomes?|chiasma\w*|crossing over|haploid|diploid)\b", 10),
            ],
        },
        {
            "slug": "cell-2-properties-and-functions",
            "name": "Cell & Its Environment (Diffusion, Osmosis & Transport)",
            "order": 3,
            "description": "Diffusion, osmosis, active transport, plasmolysis, turgidity, flaccidity, haemolysis, and crenation.",
            "patterns": [
                (r"\b(osmosis|diffusion|plasmolysis|plasmolysed|haemolysis|hemolysis|crenation|turgid\w*|flaccid\w*|hypertonic|hypotonic|isotonic|semi[- ]permeable|selectively permeable|osmotically|active transport|endocytosis|phagocytosis|pinocytosis|cyclosis)\b", 10),
            ],
        },
        {
            "slug": "nutrition-photosynthesis-food-substances",
            "name": "Nutrition in Plants & Animals (Photosynthesis & Food Substances)",
            "order": 4,
            "description": "Autotrophic/heterotrophic nutrition, photosynthesis, plant mineral nutrition, classes of food, food tests, enzymes, and deficiency diseases.",
            "patterns": [
                (r"\b(photosynthesis|chlorophyll|light stage|dark stage|calvin cycle|photolysis of water|autotrophic|heterotrophic|holozoic|saprophytic|parasitic|symbiosis|mutualism|commensalism|carnivorous plants?|insectivorous|sundew|pitcher plant|bladderwort|venus flytrap|dodder|mistletoe|chemosynthesis)\b", 10),
                (r"\b(fehling'?s|benedict'?s|biuret|millon'?s|sudan iii|iodine test|translucent spot|balanced diet|kwashiorkor|marasmus|scurvy|rickets|beriberi|pellagra|night blindness|xerophthalmia|goitre|anaemia|vitamins?\s+[a-k]|mineral salts?|amino acids?|fatty acids?|glycerol|carbohydrates?|proteins?|lipids?|macro[- ]?elements?|micro[- ]?elements?|macro[- ]?nutrients?|micro[- ]?nutrients?|trace elements?|chlorosis|reddish leaves|soil is deficient in|nutrients? to plants|manuring|fertilizers?|growth of a healthy green plant|not true of enzymes|enzymes?)\b", 10),
            ],
        },
        {
            "slug": "feeding-mechanism-digestive-system",
            "name": "Digestive System & Feeding Mechanisms",
            "order": 5,
            "description": "Mammalian dentition, dental formula, alimentary canal, digestive enzymes, absorption, and feeding adaptations in organisms.",
            "patterns": [
                (r"\b(dentition|dental formula|incisors?|canines?|premolars?|molars?|diastema|carnassial|enamel|dentine|pulp cavity|peristalsis|alimentary canal|oesophagus|stomach|duodenum|ileum|villi|lacteal|caecum|appendix|colon|rectum|digestion|assimilation)\b", 10),
                (r"\b(ptyalin|amylase|pepsin|rennin|trypsin|erepsin|lipase|maltase|sucrase|lactase|bile|emulsification|gall bladder|pancreatic juice|gastric juice|filter feed\w*|fluid feed\w*|proboscis|mandibles?|maxillae|gizzard|crop)\b", 10),
            ],
        },
        {
            "slug": "transport-system-and-mechanism",
            "name": "Transport System in Plants & Animals",
            "order": 6,
            "description": "Blood composition and functions, blood clotting, mammalian heart and blood vessels, lymphatics, transpiration, and translocation.",
            "patterns": [
                (r"\b(erythrocytes?|leucocytes?|thrombocytes?|platelets?|haemoglobin|oxyhaemoglobin|blood clotting|fibrinogen|fibrin|prothrombin|thrombin|blood plasma|lymph\w*|arteries|veins|capillaries|aorta|vena cava|pulmonary artery|pulmonary vein|hepatic portal|renal artery|pacemaker|sino[- ]atrial|systole|diastole|double circulation|open circulatory|closed circulatory)\b", 10),
                (r"\b(transpiration|potometer|translocation|root pressure|capillary action|cohesion[- ]tension|guttation|wilting)\b", 10),
            ],
        },
        {
            "slug": "gaseous-exchange-respiratory-system",
            "name": "Respiration & Gaseous Exchange",
            "order": 7,
            "description": "Aerobic and anaerobic respiration, glycolysis, Krebs cycle, respiratory organs (lungs, gills, tracheae, stomata), and breathing mechanisms.",
            "patterns": [
                (r"\b(gaseous exchange|aerobic respiration|anaerobic respiration|fermentation|lactic acid|oxygen debt|glycolysis|krebs cycle|atp|alveol\w*|bronchi\w*|trachea|larynx|diaphragm|intercostal muscles?|inhalation|exhalation|inspiration|expiration|spiracles?|tracheoles?|gills?|operculum|stomata|guard cells?|lenticels?|cutaneous respiration)\b", 10),
            ],
        },
        {
            "slug": "excretory-systems-and-mechanisms",
            "name": "Excretion & Homeostasis",
            "order": 8,
            "description": "Excretory structures (kidneys/nephrons, Malpighian tubules, flame cells, nephridia), urine formation, osmoregulation, liver, and skin.",
            "patterns": [
                (r"\b(excret\w*|nephrons?|bowman'?s capsule|glomerulus|loop of henle|proximal convoluted|distal convoluted|collecting duct|ultrafiltration|selective reabsorption|antidiuretic hormone|adh\b|osmoregulation|kidney|ureter|urinary bladder|urethra|dialysis|diuresis|nephritis|kidney stones?|flame cells?|malpighian tubules?|nephridi\w*|contractile vacuoles?|deamination|urea|detoxification|sweat glands?|homeostasis)\b", 10),
            ],
        },
        {
            "slug": "supporting-systems-and-mechanisms",
            "name": "Supporting Tissues & Skeletal System",
            "order": 9,
            "description": "Exoskeleton, endoskeleton, hydrostatic skeleton, axial and appendicular skeleton, joints, muscles, and supporting tissues in plants.",
            "patterns": [
                (r"\b(axial skeleton|appendicular skeleton|skull|cranium|vertebra\w*|cervical|atlas|axis|thoracic|lumbar|sacral|caudal|neural spine|neural canal|centrum|transverse process|zygapophys\w*|ribs?|sternum|pectoral girdle|scapula|clavicle|pelvic girdle|humerus|radius|ulna|carpals?|metacarpals?|phalanges|femur|tibia|fibula|patella|tarsals?)\b", 10),
                (r"\b(exoskeleton|endoskeleton|hydrostatic skeleton|chitin|cartilage|chondroblasts?|osteoblasts?|ball and socket|hinge joint|gliding joint|pivot joint|suture|ligaments?|tendons?|synovial|biceps|triceps|antagonistic muscles?|collenchyma|sclerenchyma|parenchyma|xylem|cambium|turgor)\b", 10),
            ],
        },
        {
            "slug": "nervous-coordination",
            "name": "Nervous, Hormonal Coordination & Sense Organs",
            "order": 10,
            "description": "Brain, spinal cord, neurones, reflex actions, endocrine glands and animal/plant hormones, tropisms, and mammalian eye and ear.",
            "patterns": [
                (r"\b(central nervous system|peripheral nervous|autonomic nervous|sympathetic|parasympathetic|cerebrum|cerebellum|medulla oblongata|hypothalamus|pituitary|spinal cord|neurones?|neurons?|dendrites?|axons?|myelin sheath|node of ranvier|synapse|acetylcholine|reflex arc|reflex action|conditioned reflex)\b", 10),
                (r"\b(endocrine|hormones?|thyroxine|adrenaline|insulin|glucagon|islets of langerhans|diabetes mellitus|oestrogen|progesterone|testosterone|auxins?|gibberellins?|cytokinins?|abscisic acid|ethene|phototropism|geotropism|hydrotropism|thigmotropism|nastic|tactic)\b", 10),
                (r"\b(mammalian eye|sclera|choroid|retina|rods and cones|fovea|yellow spot|blind spot|optic nerve|iris|pupil|aqueous humour|vitreous humour|conjunctiva|myopia|hypermetropia|astigmatism|cataract|mammalian ear|pinna|tympanum|malleus|incus|stapes|ossicles|eustachian tube|cochlea|semicircular canals?|organ of corti|olfactory|taste buds)\b", 10),
            ],
        },
        {
            "slug": "sexual-reproduction-system-behaviours",
            "name": "Reproduction in Plants & Animals",
            "order": 11,
            "description": "Asexual and vegetative reproduction, flower structure, pollination, fruits/seeds, germination, mammalian reproductive systems, and metamorphosis.",
            "patterns": [
                (r"\b(asexual reproduction|binary fission|budding|spore formation|fragmentation|vegetative propagation|runner|rhizome|corm|bulb|sucker|tuber|grafting|layering|marcotting|cutting)\b", 10),
                (r"\b(sepals?|calyx|petals?|corolla|stamens?|androecium|anther|filament|carpels?|pistils?|gynoecium|stigma|style|ovary|ovules?|pollen tube|pollination|self[- ]pollination|cross[- ]pollination|entomophilous|anemophilous|double fertilization|fertilization|endosperm|inner parts of the seed|nourish the embryo|epigeal|hypogeal|germination|placentation|axile|marginal|parietal|free central|basal|drupe|berry|legume|capsule|cypsela|caryopsis|samara|achene|schizocarp|pericarp|dispersal of fruits?|fruits? dispersed by|seeds? dispersed by)\b", 10),
                (r"\b(testes|testis|seminiferous|epididymis|vas deferens|sperm duct|prostate|seminal vesicle|ovulation|graafian follicle|corpus luteum|fallopian tube|oviduct|uterus|cervix|placenta|umbilical cord|amnion|amniotic fluid|gestation|parturition|lactation|menstrual|metamorphosis|tadpole|nymph|pupa|imago|caterpillar|maggot|courtship|viviparous|oviparous|ovoviviparous)\b", 10),
            ],
        },
        {
            "slug": "micro-organisms-and-health",
            "name": "Growth, Micro-organisms & Public Health",
            "order": 12,
            "description": "Pathogenic micro-organisms, vectors, infectious diseases (malaria, trypanosomiasis, cholera, HIV/AIDS), immunity, vaccination, and public health.",
            "patterns": [
                (r"\b(bacill\w*|cocci|coccus|spirill\w*|vibrio|staphylococc\w*|streptococc\w*|bacteri\w*|pathogen\w*|antibiotics?|penicillin|antiseptics?|disinfectants?|pasteurization|sterilization|vaccination|immunization|antibodies|antigens?|phagocytes?|unicef|world health organization|w\.h\.o|prevent and control major disease|vectors?|anopheles|plasmodium|malaria|tsetse fly|trypanosom\w*|sleeping sickness|onchocerciasis|river blindness|blackfly|simulium|schistosom\w*|bilharzia|bulinus|filariasis|elephantiasis|culex|aedes|yellow fever|dengue|cholera|typhoid|tuberculosis|poliomyelitis|measles|smallpox|hiv|aids|gonorrhoea|syphilis|ringworm)\b", 10),
            ],
        },
        {
            "slug": "basic-ecological-concepts",
            "name": "Basic Ecological Concepts, Ecosystems & Biomes",
            "order": 13,
            "description": "Ecosystem components, abiotic factors and measuring instruments, food chains/webs, ecological pyramids, nutrient cycles, and Nigerian biomes.",
            "patterns": [
                (r"\b(ecology|ecosystem|biosphere|lithosphere|hydrosphere|atmosphere|ecotone|habitat|ecological niche|autecology|synecology|biotic|abiotic|edaphic|topographic|climatic factor|distribution of organisms|anemometer|wind vane|rain gauge|hygrometer|barometer|photometer|light meter|secchi disc|quadrat|transect|pooter|sweep net|pitfall trap|tullgren funnel)\b", 10),
                (r"\b(food chain|food web|trophic level|primary producer|primary consumer|secondary consumer|tertiary consumer|decomposer|pyramid of numbers|pyramid of biomass|pyramid of energy|carbon cycle|nitrogen cycle|water cycle|nitrifying|nitrosomonas|nitrobacter|azotobacter|rhizobium|denitrifying|putrefying|sahel\b|sahelian|sudan savanna|guinea savanna|tropical rain\s*forest|mangrove swamp|montane|afro[- ]alpine|loamy|sandy|clayey|laterite|humus)\b", 14),
            ],
        },
        {
            "slug": "ecology-of-population",
            "name": "Population Ecology, Habitats & Conservation",
            "order": 14,
            "description": "Population density, succession, competition, marine/estuarine/freshwater/terrestrial habitats, soil conservation, pollution, and wildlife reserves.",
            "patterns": [
                (r"\b(population density|population size|overcrowding|carrying capacity|natality|mortality|emigration|immigration|ecological succession|primary succession|secondary succession|pioneer community|climax community|intra[- ]specific|inter[- ]specific competition|predation|biological control)\b", 10),
                (r"\b(estuarine|estuary|brackish|intertidal|littoral|benthic|pelagic|aphotic|photic|freshwater|arboreal|xerophytes?|hydrophytes?|mesophytes?|halophytes?|pneumatophores?|afforestation|deforestation|reforestation|desertification|soil erosion|leaching|mulching|crop rotation|bush burning|poaching|game reserve|yankari|conserving wildlife|conservation|non[- ]?bio\s*degradable|biodegradable|pollutants?)\b", 10),
            ],
        },
        {
            "slug": "genetics-the-science-of-heredity",
            "name": "Variation & Genetics (Heredity)",
            "order": 15,
            "description": "Morphological and physiological variation, Mendel's laws, monohybrid/dihybrid crosses, sex-linked traits, blood groups, DNA/RNA, and mutations.",
            "patterns": [
                (r"\b(genetics|heredity|mendel\w*|monohybrid|dihybrid|alleles?|allelomorph\w*|homozygous|heterozygous|dominant|recessive|genotype|phenotype|f_?1 generation|f_?2 generation|test cross|back cross|co[- ]dominance|incomplete dominance|sex[- ]linked|sex[- ]linkage|haemophilia|colour blindness|baldness|polygenic|mutation|mutagens?|albinism|sickle[- ]cell|down'?s syndrome|klinefelter|turner'?s syndrome)\b", 10),
                (r"\b(dna|deoxyribonucleic|rna|ribonucleic|nucleotide|adenine|thymine|guanine|cytosine|uracil|double helix|watson and crick|chromosomes?|genes?|locus|blood groups?|abo|rhesus|universal donor|universal recipient|paternity|continuous variation|discontinuous variation|morphological variation|physiological variation|fingerprints?)\b", 10),
            ],
        },
        {
            "slug": "variations-adaptation-for-survival-evolution",
            "name": "Adaptation & Evolution",
            "order": 16,
            "description": "Structural and behavioural adaptations, social insects, Lamarck's and Darwin's theories of evolution, and evidence of evolution.",
            "patterns": [
                (r"\b(organic evolution|lamarck\w*|use and disuse|acquired characteristics|darwin\w*|natural selection|survival of the fittest|neo[- ]darwinism|fossil records?|palaeontology|comparative anatomy|homologous structures?|analogous structures?|vestigial organs?|divergent evolution|convergent evolution|adaptive radiation|industrial melanism|peppered moth)\b", 10),
                (r"\b(adaptation|adapted for|adapted to|webbed feet|beaks?|claws?|talons?|camels?|streamlined body|lateral line|locomotion in water|camouflage|cryptic colou?ration|warning colou?ration|mimicry|batesian|mullerian|countershading|aestivation|hibernation|migration|basking|endotherm\w*|ectotherm\w*|poikilotherm\w*|homoiotherm\w*|social insects?|termites?|castes?|nuptial flight|worker bee|queen bee|drone)\b", 10),
            ],
        },
    ],
    "english-language": [
        {
            "slug": "comprehension",
            "name": "Reading Comprehension, Summary & Composition",
            "order": 1,
            "description": "Reading comprehension passages, inference, author's tone/purpose, summary writing, and continuous essay/letter composition.",
            "patterns": [
                (r"\b(read the following passage|according to the passage|in the passage|the writer|the author|from the passage|the passage suggests|the passage states|the text states|according to the text|suitable titt?le for the passage|central theme of the passage|tone of the passage|write a story|write an article|write a letter|write a speech|school magazine)\b", 35),
            ],
        },
        {
            "slug": "english-grammar",
            "name": "Prescribed Literature Texts & Literary Appreciation",
            "order": 2,
            "description": "JAMB/WAEC prescribed novels (The Lekki Headmaster, The Life Changer, Sweet Sixteen, In Dependence) and figures of speech.",
            "patterns": [
                (r"\b(lekki headmaster|kabir garba|bepo|stardom|ikenna|the life changer|khadija abubakar|salma|sweet sixteen|bolaji abdullahi|aliyah?|in dependence|sarah ladipo|tayo|vanessa|last days at forcados|mohammed|efua|jimi|sola|nene|ansel|mr\.?\s*mallum|novel|chapter\s+\d+|figure of speech|metaphor|simile|personification|hyperbole|oxymoron|euphemism|irony|synecdoche|metonymy|alliteration|assonance)\b", 30),
            ],
        },
        {
            "slug": "antonyms-synonyms-homonyms",
            "name": "Synonyms (Nearest in Meaning)",
            "order": 3,
            "description": "Words and expressions nearest in meaning in context.",
            "patterns": [
                (r"\b(nearest in meaning|closest in meaning|same meaning as|most likely mean in the context|synonym\w*|replace the underlined word)\b", 35),
            ],
        },
        {
            "slug": "word-classes",
            "name": "Antonyms (Opposite in Meaning)",
            "order": 4,
            "description": "Words and expressions most nearly opposite in meaning in context.",
            "patterns": [
                (r"\b(opposite in meaning|most nearly opposite|antonym\w*)\b", 35),
            ],
        },
        {
            "slug": "sentence-interpretation",
            "name": "Idioms, Figurative Expressions & Sentence Interpretation",
            "order": 5,
            "description": "Idiomatic expressions, proverbs, and selecting the most appropriate interpretation of a sentence.",
            "patterns": [
                (r"\b(interpretation that is most appropriate|most appropriate interpretation|possible interpretations of|this means that|what does this sentence mean|idiom\w*|figurative|proverb)\b", 35),
            ],
        },
        {
            "slug": "language-registers",
            "name": "Lexis, Structure & Register (Cloze & Vocabulary)",
            "order": 6,
            "description": "Register passages with numbered gaps, specialized vocabulary in context, and lexical sentence completion.",
            "patterns": [
                (r"(\bin question number(?:ed)?\s+\d+|\bfills? the gap labelled\s+\d+|\bnumbered gaps?|\bmissing words? in the passage|\bfill each of the numbered|\bregister of|\bmost suitable word to fill gap|-\d{1,3}-)", 35),
                (r"\b(fill (?:in )?the gaps?|fill each gap|choose the word or group of words that best completes|choose the word that best completes|choose the (?:best )?option (?:from letters .* )?that (?:best )?completes? the gap)\b", 5),
            ],
        },
        {
            "slug": "oral-english",
            "name": "Oral English: Vowel & Consonant Sounds",
            "order": 7,
            "description": "Phonetic symbols, monophthongs, diphthongs, triphthongs, voiced/voiceless consonants, and silent letters.",
            "patterns": [
                (r"\b(same vowel sound|same consonant sound|vowel sound as|consonant sound as|underlined sound|phonetic symbol|monophthong|diphthong|triphthong|plosive|fricative|affricate|nasal|approximant|voiceless|voiced|silent letter)\b", 35),
                (r"(/[iɪeæɑɒɔʊuʌɜəaɪeɪɔɪaʊəʊɪəeəʊəptkbdgfvθðszʃʒʧʤmnŋlrjwː]+/)", 15),
            ],
        },
        {
            "slug": "stress",
            "name": "Oral English: Stress, Rhymes & Intonation",
            "order": 8,
            "description": "Word syllable stress, emphatic/contrastive stress, rhymes, and intonation patterns.",
            "patterns": [
                (r"\b(emphatic stress|primary stress|different stress pattern|appropriate stress pattern|stress pattern|stressed syllables?|stressed on the (?:first|second|third|fourth) syllable|syllable stress|rhymes? with|intonation|falling tune|rising tune|capitalized word|word in capital)\b", 35),
            ],
        },
        {
            "slug": "question-tag",
            "name": "Question Tags, Modals & Pronouns",
            "order": 9,
            "description": "Question tags, modal auxiliaries, reflexive/reciprocal/relative pronouns, and determiners.",
            "patterns": [
                (r"\b(isn'?t it|aren'?t i|aren'?t they|wasn'?t he|wasn'?t she|weren'?t they|don'?t you|doesn'?t he|doesn'?t she|didn'?t they|didn'?t he|didn'?t she|haven'?t you|hasn'?t he|hadn'?t they|won'?t you|shan'?t we|can'?t he|shouldn'?t you|wouldn'?t he|needn'?t|daren'?t|question tag|whose\s*\|\s*whom|whom\s*\|\s*who)\b", 12),
                (r"\b(each other|one another|either|neither|none of the|every one of|much|many|little|a little|few|a few)\b", 7),
            ],
        },
        {
            "slug": "concord",
            "name": "Concord (Subject-Verb Agreement)",
            "order": 10,
            "description": "Grammatical, notional, and proximity concord; collective and uncountable nouns.",
            "patterns": [
                (r"\b(as well as|together with|along with|in addition to|no less than|neither .* nor|either .* or|not only .* but also|one of the .* who|each of the|every one of the|the number of|a number of|police|cattle|poultry|vermin|clergy|gentry|furniture|equipment|information|luggage|baggage|advice|news|measles|mumps|rickets|billiards)\b", 10),
            ],
        },
        {
            "slug": "tense-and-aspect",
            "name": "Tenses, Aspect & Conditionals",
            "order": 11,
            "description": "Sequence of tenses, subjunctive ('it is high time', 'would rather'), and conditional clauses.",
            "patterns": [
                (r"\b(it is high time|it is time|it is about time|would rather|had better|if i were|had i known|if he had|if she had|by the time|since\s+\d{4}|for the past|for ten years|since morning|used to|be used to|get used to|have been|had been|will have been|has been away|expects\s*/\s*would)\b", 10),
            ],
        },
        {
            "slug": "phrasal-verb",
            "name": "Prepositions, Phrasal Verbs & Collocations",
            "order": 12,
            "description": "Prepositional collocations and phrasal verbs in context.",
            "patterns": [
                (r"\b(accused of|acquitted of|congratulate .* on|insist on|persist in|consist of|consist in|comprise|dispense with|dispose of|abide by|comply with|conducive to|prefer .* to|superior to|inferior to|senior to|junior to|prior to|good at|bad at|afraid of|proud of|jealous of|envious of|fond of|capable of|guilty of|innocent of|charged with|suffer from|die of|die from|result in|result from|look forward to|with a view to|put up with|make up for|made for|made at|call off|turn down|give in|give up|bring about|carry out|pass away|run out of|break down|break out|take after|take off|set off|set out|stand by|stand for|make out|round off|round up|with\s*\|\s*in\s*\|\s*for\s*\|\s*by)\b", 10),
            ],
        },
        {
            "slug": "clauses",
            "name": "Clauses, Phrases, Voice & Reported Speech",
            "order": 13,
            "description": "Grammatical names and functions of clauses/phrases, active/passive voice, and direct/indirect speech.",
            "patterns": [
                (r"\b(grammatical name|grammatical function|adverbial clause|adjectival clause|relative clause|noun clause|noun phrase|adverbial phrase|prepositional phrase|modifies the noun|qualifies the noun|modifies the verb|object of the verb|subject of the verb|complement of|in apposition to|passive voice|active voice|indirect speech|reported speech|no sooner .* than|hardly .* when|scarcely .* when|barely .* when|so .* that|such .* that|too .* to)\b", 10),
            ],
        },
        {
            "slug": "the-spelling-rules",
            "name": "Spelling, Punctuation & Word Formation",
            "order": 14,
            "description": "Correctly spelt words, prefixes, suffixes, capitalization, and punctuation marks.",
            "patterns": [
                (r"\b(correctly spelt|correct spelling|misspelt|wrongly spelt|prefix|suffix|punctuation|apostrophe|hyphen|colon|semicolon|inverted commas|quotation marks|accommodation|embarrass\w*|occasi?on\w*|committee|maintenance|privilege|separate|pronunciation|questionnaire|millennium|diarrhoea|auxiliary|omission)\b", 10),
            ],
        },
    ],
}

# Pre-compile regex patterns for speed across 30,000+ questions
COMPILED_TOPICS = {}
for _subj, _topic_list in CANONICAL_TOPICS.items():
    COMPILED_TOPICS[_subj] = []
    for _t in _topic_list:
        COMPILED_TOPICS[_subj].append({
            "slug": _t["slug"],
            "name": _t["name"],
            "order": _t["order"],
            "description": _t.get("description", ""),
            "compiled_patterns": [(re.compile(pat, re.IGNORECASE), w) for pat, w in _t["patterns"]],
        })

# Maps specific ground-truth scraper slugs (from all_questions.jsonl) to canonical topic slugs.
# Broad macro-buckets (e.g. 'basic-chemistry', 'geometry-and-trigonometry', 'algebra') are excluded
# here so Tier-2 regex scoring classifies them into their exact canonical topic.
GROUND_TRUTH_TOPIC_MAP = {
    "chemistry": {
        "matter-and-separation-techniques": "matter-and-separation-techniques",
        "particulate-nature-of-matter": "particulate-nature-of-matter",
        "radioactivity-nuclear-chemistry": "atomic-structure-and-periodic-table",
        "atomic-structure-and-bonding": "atomic-structure-and-periodic-table",
        "periodic-table": "periodic-table",
        "chemical-combinations": "chemical-combinations",
        "chemical-bonding": "chemical-combinations",
        "shapes-of-molecules-and-solids": "chemical-combinations",
        "quantitative-and-qualitative-analyses": "stoichiometry-mole-concept",
        "mass-volume-concepts": "stoichiometry-mole-concept",
        "properties-of-gases-gas-laws": "properties-of-gases-gas-laws",
        "properties-of-solids-and-liquids": "properties-of-gases-gas-laws",
        "water-and-solubility-concept": "water-and-solubility-concept",
        "unsaturated-saturated-and-supersaturated-solutions": "water-and-solubility-concept",
        "air-and-air-pollution": "air-and-air-pollution",
        "acids-bases-and-salts": "acids-bases-and-salts",
        "types-of-reactions": "electrochemistry-and-redox",
        "electrodes-electrochemical-series-and-electrolysis": "electrodes-electrochemical-series-and-electrolysis",
        "energy-and-chemical-reactions": "energy-and-chemical-reactions",
        "endothermic-and-exothermic-reactions": "energy-and-chemical-reactions",
        "reactions-rates-and-chemical-equilibria": "kinetics-energetics-and-equilibrium",
        "chemical-equilibrium": "kinetics-energetics-and-equilibrium",
        "carbon-carbon-compounds": "non-metals-and-their-compounds",
        "sulphur-sulphur-compounds": "non-metals-and-their-compounds",
        "halogen-family": "non-metals-and-their-compounds",
        "oxygen-oxides-ozone": "non-metals-and-their-compounds",
        "hydrogen-hydrides": "non-metals-and-their-compounds",
        "nitrogen-nitrogen-compounds": "non-metals-and-their-compounds",
        "transition-metals-and-their-compounds": "metals-and-their-compounds-1",
        "metals-and-their-compounds-1": "metals-and-their-compounds-1",
        "hydrocarbons": "hydrocarbons",
        "basic-concepts-of-organic-chemistry": "hydrocarbons",
        "crude-oil": "hydrocarbons",
        "organic-chemistry": "organic-chemistry",
        "organic-chemistry-2": "organic-chemistry",
    },
    "mathematics": {
        "number-bases": "number-bases",
        "modular-arithmetic": "number-bases",
        "fractions-decimals-percentages-and-approximation": "fractions-decimals-percentages-and-approximation",
        "ratios-proportions-and-rates": "fractions-decimals-percentages-and-approximation",
        "financial-arithmetic": "fractions-decimals-percentages-and-approximation",
        "indices": "indices-logarithms-and-surds",
        "logarithms": "indices-logarithms-and-surds",
        "surds": "indices-logarithms-and-surds",
        "sets": "sets",
        "logic": "sets",
        "change-of-subject-of-formula": "polynomials",
        "simple-operations-on-algebraic-expression": "polynomials",
        "algebraic-fractions": "polynomials",
        "polynomials": "polynomials",
        "functions-and-relations": "polynomials",
        "quadratic-equations": "quadratic-equations",
        "solution-of-linear-equations": "quadratic-equations",
        "graph-of-linear-and-quadratic-functions": "quadratic-equations",
        "linear-inequalities": "linear-inequalities",
        "variations": "variations",
        "progressions": "progressions",
        "matrices-and-determinants": "matrices-and-determinants",
        "binary-operations": "matrices-and-determinants",
        "triangles-and-polygons": "circles",
        "angles-and-intercepts-on-parallel-lines": "circles",
        "construction": "circles",
        "circles": "circles",
        "mensuration": "mensuration",
        "lengths-and-perimeters": "mensuration",
        "areas": "mensuration",
        "volumes": "mensuration",
        "coordinate-geometry-of-straight-lines": "coordinate-geometry-of-straight-lines",
        "bearings-and-distances": "trigonometric-ratios",
        "angles-of-elevation-and-depression": "trigonometric-ratios",
        "trigonometric-ratios": "trigonometric-ratios",
        "differentiation": "differentiation",
        "application-of-differentiation": "differentiation",
        "integration": "integration",
        "application-of-integration": "integration",
        "statistics": "statistics",
        "representation-of-data": "statistics",
        "measures-of-location": "statistics",
        "measures-of-dispersion": "statistics",
        "probability": "probability",
        "permutation-and-combination": "probability",
    },
    "physics": {
        "measurement": "measurement",
        "fundamental-and-derived-quantities-1": "measurement",
        "scalars-and-vectors": "scalars-and-vectors",
        "linear-motion": "linear-motion",
        "projectile-motion": "linear-motion",
        "momentum-impulse-newtons-law-of-motion": "momentum-impulse-newtons-law-of-motion",
        "friction": "momentum-impulse-newtons-law-of-motion",
        "equilibrium-of-forces-1": "equilibrium-of-forces-1",
        "density-and-relative-density": "equilibrium-of-forces-1",
        "energy-and-power": "work-energy-power",
        "simple-machine": "work-energy-power",
        "work-energy-power": "work-energy-power",
        "motion-force-circular-motion": "simple-harmonic-motion-1",
        "simple-harmonic-motion-1": "simple-harmonic-motion-1",
        "gravitational-field-1": "simple-harmonic-motion-1",
        "satellite-and-rocket-1": "simple-harmonic-motion-1",
        "deformation-of-solids": "deformation-of-solids",
        "simple-structure-of-matter": "deformation-of-solids",
        "heat-and-temperature": "heat-and-temperature",
        "heat-energy": "heat-energy",
        "measurement-of-heat-energy-1": "heat-energy",
        "evaporation-and-boiling": "heat-energy",
        "heat-transfer": "thermodynamics",
        "sound-wave": "waves-1",
        "waves-1": "waves-1",
        "vibration-in-springs-and-pipes": "waves-1",
        "wave": "waves-1",
        "reflection-of-light": "reflection-of-light",
        "refraction-of-light": "reflection-of-light",
        "application-of-lens": "application-of-lens",
        "electric-field-2": "electric-field-1",
        "electric-field-1": "electric-field-1",
        "current-electricity-1": "current-electricity-1",
        "simple-ac-circuit": "magnetic-field-1",
        "electromagnetic-field-1": "magnetic-field-1",
        "magnetic-field-1": "magnetic-field-1",
        "structure-of-the-nucleus": "modern-physics-and-nuclear-physics",
        "structure-of-the-atom": "modern-physics-and-nuclear-physics",
        "semi-conductor": "modern-physics-and-nuclear-physics",
        "wave-particle-paradox": "modern-physics-and-nuclear-physics",
        "atomic-physics": "modern-physics-and-nuclear-physics",
        "electrical-conduction-through-liquids-and-gases-1": "modern-physics-and-nuclear-physics",
    },
    "biology": {},
    "english-language": {},
}

# Fallback high-frequency topic per subject when a question has minimal text (e.g. pure image stem with numeric options)
DEFAULT_FALLBACK_SLUG = {
    "chemistry": "stoichiometry-mole-concept",
    "mathematics": "circles",
    "physics": "current-electricity-1",
    "biology": "classification-or-organisation-of-life",
    "english-language": "language-registers",
}

_GROUND_TRUTH_BY_SOURCE_ID = None
_GROUND_TRUTH_BY_NORM_TEXT = None


def _clean_for_matching(text: str) -> str:
    if not text:
        return ""
    s = html.unescape(text).lower()
    s = s.replace("’", "'").replace("‘", "'").replace("−", "-")
    return s


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", _clean_for_matching(text).strip())[:240]


def _load_ground_truth_index():
    global _GROUND_TRUTH_BY_SOURCE_ID, _GROUND_TRUTH_BY_NORM_TEXT
    if _GROUND_TRUTH_BY_SOURCE_ID is not None:
        return

    _GROUND_TRUTH_BY_SOURCE_ID = {}
    _GROUND_TRUTH_BY_NORM_TEXT = {}

    candidate_paths = [
        Path("/app/myschool_dataset/all_questions.jsonl"),
        Path("/home/kalmin/startups/myschool-past-questions-scraper/myschool_dataset/all_questions.jsonl"),
    ]
    jsonl_path = next((p for p in candidate_paths if p.exists()), None)
    if not jsonl_path:
        return

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                raw_topic = row.get("topic")
                subj = row.get("subject")
                if not raw_topic or not subj:
                    continue
                mapped = GROUND_TRUTH_TOPIC_MAP.get(subj, {}).get(raw_topic)
                if not mapped:
                    continue
                sid = row.get("id")
                if sid:
                    _GROUND_TRUTH_BY_SOURCE_ID[str(sid)] = mapped
                qtext = row.get("question_text") or ""
                if len(qtext) >= 20:
                    _GROUND_TRUTH_BY_NORM_TEXT[(subj, _normalize_text(qtext))] = mapped
    except Exception:
        pass


def classify_question_topic(
    subject_slug: str,
    question_text: str,
    explanation: str = "",
    options_text: str = "",
    source_id: str = None,
    raw_topic_slug: str = None,
):
    """
    Returns (canonical_slug, score, method) for a question.
    - Tier 1: Explicit raw_topic_slug or ground-truth index from all_questions.jsonl
    - Tier 2: Multi-field weighted regex scorer (question_text x2.2 + options x1.4 + explanation x1.2)
    - Tier 3: Subject default fallback slug
    """
    if subject_slug not in COMPILED_TOPICS:
        return None, 0.0, "unknown_subject"

    # Tier 1a: Explicit raw_topic_slug passed from scraper/JSONL
    if raw_topic_slug:
        mapped = GROUND_TRUTH_TOPIC_MAP.get(subject_slug, {}).get(raw_topic_slug)
        if mapped:
            return mapped, 100.0, "ground_truth_raw_slug"

    # Tier 1b: Ground-truth lookup from all_questions.jsonl
    _load_ground_truth_index()
    if source_id and str(source_id) in _GROUND_TRUTH_BY_SOURCE_ID:
        return _GROUND_TRUTH_BY_SOURCE_ID[str(source_id)], 100.0, "ground_truth_source_id"

    norm_q = _normalize_text(question_text)
    if len(norm_q) >= 20 and (subject_slug, norm_q) in _GROUND_TRUTH_BY_NORM_TEXT:
        return _GROUND_TRUTH_BY_NORM_TEXT[(subject_slug, norm_q)], 100.0, "ground_truth_text"

    # Tier 2: Multi-field weighted regex scoring
    text_low = _clean_for_matching(question_text)
    opts_low = _clean_for_matching(options_text)
    exp_low = _clean_for_matching(explanation)

    best_slug = None
    best_score = 0.0

    for topic in COMPILED_TOPICS[subject_slug]:
        slug = topic["slug"]
        score = 0.0
        for regex, weight in topic["compiled_patterns"]:
            m_txt = len(regex.findall(text_low))
            m_opt = len(regex.findall(opts_low))
            m_exp = len(regex.findall(exp_low))
            if m_txt:
                score += weight * 2.2 * min(m_txt, 3)
            if m_opt:
                score += weight * 1.4 * min(m_opt, 2)
            if m_exp:
                score += weight * 1.2 * min(m_exp, 3)
        if score > best_score:
            best_score = score
            best_slug = slug

    if best_slug and best_score > 0:
        return best_slug, best_score, "weighted_classifier"

    # Tier 3: Subject fallback
    fallback_slug = DEFAULT_FALLBACK_SLUG.get(subject_slug, COMPILED_TOPICS[subject_slug][0]["slug"])
    return fallback_slug, 0.0, "fallback"
