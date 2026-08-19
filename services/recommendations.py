GENERIC_PRECAUTIONS = [
    "Inspect nearby plants before deciding treatment.",
    "Use clean tools and avoid handling wet plants.",
    "Keep future scans from a similar distance and angle when possible.",
]

GENERIC_AVOID = [
    "Do not apply pesticide or fertilizer only because the app is uncertain.",
    "Do not remove large amounts of foliage unless symptoms are clearly spreading.",
]

GENERIC_NEXT_CHECK = [
    "Upload a closer, well-lit image of the affected leaf or plant part.",
    "Compare one affected area with a healthy nearby plant.",
    "Record whether symptoms are spreading after rain or irrigation.",
]

DEFAULT_VISUAL_INDICATORS = [
    "The classifier matched the uploaded image to a crop-specific PlantVillage class.",
    "Use the original photo and the farmer observation together before deciding treatment.",
]

DEFAULT_PREVENTION = [
    "Avoid overhead watering late in the day.",
    "Remove fallen diseased leaves and keep the field clean.",
    "Improve plant spacing and airflow where possible.",
]

DEFAULT_MEDICINE_GUIDANCE = [
    "Use chemical treatment only after symptoms are visible on multiple leaves or confirmed locally.",
    "Follow the local agriculture officer's advice and the product label for crop, dose, interval, and safety period.",
]

DEFAULT_FERTILIZER_GUIDANCE = [
    "Do not add fertilizer as a disease treatment unless nutrient deficiency is also visible.",
    "Use balanced nutrition and avoid excess nitrogen during active leaf disease.",
]

DEFAULT_NATURAL_REMEDIES = [
    "Remove badly affected leaves and dispose of them away from healthy plants.",
    "Use soil-level watering and improve airflow to reduce leaf wetness.",
    "Keep a clean field floor and rescan before escalating treatment.",
]

DEFAULT_EXPERT_CONFIRMATION = (
    "Get local expert confirmation if symptoms spread quickly, the plant is severely affected, "
    "or chemical treatment is being considered."
)


DISEASE_KNOWLEDGE = {
    ("tomato", "early blight"): {
        "symptoms": [
            "Brown spots with ring-like patterns are common for this problem.",
            "Older lower leaves often yellow first.",
            "Symptoms may expand after leaves stay wet.",
        ],
        "possible_causes": [
            "Fungal leaf disease favored by wet foliage and crop residue.",
            "Plant stress can make the crop more vulnerable.",
        ],
        "recommendations": [
            "Remove the worst affected lower leaves and keep debris away from the crop.",
            "Improve airflow around plants and avoid wetting foliage in the evening.",
            "Use a locally registered fungicide only if new spots continue to appear.",
        ],
        "visual_indicators": [
            "Brown circular leaf spots with ring-like bands.",
            "Yellowing around older lower leaves.",
            "Spots beginning from the lower canopy.",
        ],
        "preventive_measures": [
            "Mulch soil to reduce rain splash onto lower leaves.",
            "Rotate tomatoes away from old tomato or potato beds.",
            "Prune lower leaves carefully to increase airflow.",
        ],
        "medicine_guidance": [
            "If spread continues, ask for a locally registered protectant fungicide suitable for tomato early blight.",
            "Follow label instructions exactly for dose, interval, harvest waiting period, and protective gear.",
        ],
        "fertilizer_guidance": [
            "Avoid nitrogen-heavy feeding during active leaf spotting.",
            "Maintain balanced potassium and calcium nutrition if your local soil test supports it.",
        ],
        "natural_remedies": [
            "Remove infected lower leaves and keep them out of compost near the crop.",
            "Water at soil level and keep leaves dry.",
            "Use mulch to reduce soil splash during rain.",
        ],
        "precautions": [
            "Sanitize hands or tools after removing affected leaves.",
            "Water at soil level where possible.",
            "Rescan the same plant in 2 to 3 days.",
        ],
        "do_not": [
            "Do not apply extra nitrogen as the first response.",
            "Do not compost infected leaf debris beside the crop.",
        ],
        "next_check": [
            "Check lower leaves for circular brown spots with yellowing around them.",
            "Inspect whether spots are moving upward through the canopy.",
        ],
        "follow_up": "Repeat a close-up leaf scan in 48 to 72 hours.",
    },
    ("tomato", "late blight"): {
        "symptoms": [
            "Water-soaked brown patches may appear near leaf edges.",
            "Rapid darkening can occur during humid weather.",
            "White growth may appear on leaf undersides when conditions are wet.",
        ],
        "possible_causes": [
            "Oomycete-like late blight favored by cool, wet, humid conditions.",
        ],
        "recommendations": [
            "Remove heavily affected leaves carefully and keep them away from the field.",
            "Stop overhead irrigation and improve airflow around plants.",
            "Ask a local agriculture officer about registered protectant options if spread continues.",
        ],
        "visual_indicators": [
            "Water-soaked brown or dark leaf patches.",
            "Fast expansion during cool, wet, humid weather.",
            "Possible pale growth on leaf undersides.",
        ],
        "preventive_measures": [
            "Avoid overhead irrigation.",
            "Increase spacing and airflow.",
            "Remove infected plant material promptly.",
        ],
        "medicine_guidance": [
            "Late blight can spread fast; seek local advice about registered tomato late-blight fungicide options.",
            "Do not mix or repeat products without label guidance and expert advice.",
        ],
        "fertilizer_guidance": [
            "Fertilizer will not cure late blight.",
            "Keep nutrition balanced, but focus first on sanitation, moisture control, and confirmed treatment.",
        ],
        "natural_remedies": [
            "Remove badly infected leaves or plants carefully.",
            "Keep foliage dry and improve airflow.",
            "Separate infected material from healthy crop rows.",
        ],
        "precautions": [
            "Avoid walking through wet plants because disease can spread easily.",
            "Keep records of weather and symptom spread.",
            "Rescan within 24 to 48 hours if patches are expanding.",
        ],
        "do_not": [
            "Do not compost infected material near healthy plants.",
            "Do not delay local confirmation if symptoms spread quickly.",
        ],
        "next_check": [
            "Look for fresh water-soaked lesions at leaf edges.",
            "Check the underside of leaves for pale fungal growth.",
        ],
        "follow_up": "Rescan the same row or plant section within 24 to 48 hours.",
    },
    ("tomato", "tomato yellow leaf curl virus"): {
        "symptoms": [
            "Upward leaf curling and yellowing are typical warning signs.",
            "New growth can look stunted or distorted.",
        ],
        "possible_causes": [
            "Viral disease commonly spread by whiteflies.",
        ],
        "recommendations": [
            "Inspect undersides of leaves for whiteflies during the morning.",
            "Use yellow sticky traps and remove severely affected plants after confirmation.",
            "Seek local advice for whitefly-safe pesticide rotation if insects are present.",
        ],
        "visual_indicators": [
            "Upward curling of leaves.",
            "Yellowing and stunted new growth.",
            "Reduced flowering or fruit setting.",
        ],
        "preventive_measures": [
            "Use insect netting for young plants where possible.",
            "Control weeds that can host whiteflies.",
            "Monitor whitefly numbers with yellow sticky traps.",
        ],
        "medicine_guidance": [
            "If whiteflies are present, ask for a locally recommended insecticide rotation safe for tomato.",
            "Rotate insecticide groups only under local guidance to reduce resistance.",
        ],
        "fertilizer_guidance": [
            "Fertilizer will not cure a viral disease.",
            "Avoid excess nitrogen because soft new growth can attract pests.",
        ],
        "natural_remedies": [
            "Use yellow sticky traps.",
            "Remove heavily infected plants after local confirmation.",
            "Use netting or physical barriers for young plants.",
        ],
        "precautions": [
            "Protect young plants with netting where possible.",
            "Control weeds that host whiteflies.",
            "Monitor nearby tomato plants for similar curling.",
        ],
        "do_not": [
            "Do not save seed from suspected infected plants.",
            "Do not repeatedly use the same insecticide group.",
        ],
        "next_check": [
            "Check for whiteflies on the underside of new leaves.",
            "Compare new growth with healthy plants of the same age.",
        ],
        "follow_up": "Scan new growth again in 2 to 3 days and record whitefly presence.",
    },
    ("potato", "early blight"): {
        "symptoms": [
            "Older leaves may show brown spots with ring-like markings.",
            "Yellowing can spread from lower leaves upward.",
        ],
        "possible_causes": [
            "Fungal disease encouraged by leaf wetness and plant stress.",
        ],
        "recommendations": [
            "Remove the most affected lower leaves when practical.",
            "Keep irrigation balanced and avoid drought stress.",
            "Use crop rotation and avoid planting potato after tomato in the same bed.",
        ],
        "visual_indicators": [
            "Brown spots with concentric ring patterns.",
            "Yellowing lower leaves.",
            "Slow upward movement from older foliage.",
        ],
        "preventive_measures": [
            "Rotate away from tomato and potato family crops.",
            "Avoid soil splash on lower leaves.",
            "Maintain steady soil moisture.",
        ],
        "medicine_guidance": [
            "If symptoms expand, ask for a locally registered potato early-blight fungicide.",
            "Follow label instructions and avoid unnecessary repeat sprays.",
        ],
        "fertilizer_guidance": [
            "Balanced nutrition can reduce stress, but fertilizer is not a direct cure.",
            "Avoid overusing nitrogen if foliage disease is active.",
        ],
        "natural_remedies": [
            "Remove affected lower leaves when the crop can tolerate it.",
            "Keep soil splash down with mulch or careful watering.",
            "Improve row airflow.",
        ],
        "precautions": [
            "Scout lower canopy after rainy or humid days.",
            "Avoid splashing soil onto lower leaves.",
        ],
        "do_not": [
            "Do not ignore lower leaf symptoms if they are moving upward.",
            "Do not use blanket pesticide without checking spread and weather.",
        ],
        "next_check": [
            "Inspect lower leaves for ring-like spots.",
            "Check whether new spots are appearing on younger leaves.",
        ],
        "follow_up": "Rescan in 2 to 3 days from the same row.",
    },
    ("potato", "late blight"): {
        "symptoms": [
            "Dark irregular lesions can spread rapidly.",
            "Leaves may collapse in humid, cloudy weather.",
        ],
        "possible_causes": [
            "Late blight favored by humid nights, leaf wetness, and cool weather.",
        ],
        "recommendations": [
            "Remove infected foliage carefully if only a small area is affected.",
            "Improve drainage and stop wetting leaves.",
            "Follow local fungicide guidance quickly if symptoms are spreading.",
        ],
        "visual_indicators": [
            "Dark irregular leaf lesions.",
            "Rapid leaf collapse in humid weather.",
            "Possible pale growth on leaf undersides.",
        ],
        "preventive_measures": [
            "Avoid evening overhead irrigation.",
            "Improve field drainage.",
            "Destroy infected residue after harvest.",
        ],
        "medicine_guidance": [
            "Seek local advice quickly for registered late-blight protection if symptoms are spreading.",
            "Respect pre-harvest intervals and safety label instructions.",
        ],
        "fertilizer_guidance": [
            "Fertilizer will not stop late blight.",
            "Keep plants from drought stress but prioritize moisture control and confirmed treatment.",
        ],
        "natural_remedies": [
            "Remove and isolate infected foliage carefully.",
            "Avoid moving through wet rows.",
            "Keep leaves as dry as possible.",
        ],
        "precautions": [
            "Avoid moving through wet potato rows.",
            "Separate badly affected plant material from healthy produce.",
        ],
        "do_not": [
            "Do not store tubers from badly affected plants with healthy tubers.",
            "Do not irrigate late evening during humid weather.",
        ],
        "next_check": [
            "Check leaf undersides for pale growth in wet conditions.",
            "Inspect nearby plants for fresh dark lesions.",
        ],
        "follow_up": "Rescan within 24 hours if the weather remains wet.",
    },
    ("maize", "common rust"): {
        "symptoms": [
            "Reddish-brown pustules may form on leaf surfaces.",
            "Rust marks can reduce green leaf area when severe.",
        ],
        "possible_causes": [
            "Fungal rust favored by high humidity and moderate temperatures.",
        ],
        "recommendations": [
            "Scan multiple leaves from lower and middle canopy.",
            "Improve spacing where plants are too dense.",
            "Follow local maize advisory before applying fungicide.",
        ],
        "visual_indicators": [
            "Reddish-brown pustules on maize leaves.",
            "Powdery rust marks that may rub off.",
            "More concern if symptoms reach upper leaves before tasseling.",
        ],
        "preventive_measures": [
            "Use resistant hybrids in future seasons where rust repeats.",
            "Avoid very dense planting.",
            "Scout after humid weather.",
        ],
        "medicine_guidance": [
            "If rust reaches upper leaves or spreads before tasseling, ask for a locally registered maize fungicide recommendation.",
            "Use fungicide only when crop stage and disease pressure justify it.",
        ],
        "fertilizer_guidance": [
            "Keep balanced crop nutrition to reduce stress.",
            "Do not use fertilizer as a rust treatment.",
        ],
        "natural_remedies": [
            "Improve airflow by managing weeds and dense edges.",
            "Track spread on the same leaves over the next scan.",
            "Remove volunteer maize or grassy hosts where relevant.",
        ],
        "precautions": [
            "Watch upper leaves before tasseling.",
            "Use resistant hybrids next season if rust pressure repeats.",
        ],
        "do_not": [
            "Do not judge severity from one leaf only.",
            "Do not delay local advice if pustules spread to upper leaves.",
        ],
        "next_check": [
            "Check whether marks rub off as powdery rust.",
            "Inspect upper leaves for new pustules.",
        ],
        "follow_up": "Rescan the same plants in 3 to 5 days.",
    },
    ("maize", "northern leaf blight"): {
        "symptoms": [
            "Long grey-green or tan lesions may develop on maize leaves.",
            "Symptoms often expand after cloudy wet days.",
        ],
        "possible_causes": [
            "Fungal leaf blight that spreads with leaf wetness.",
        ],
        "recommendations": [
            "Mark the row and rescan the same leaves in 48 hours.",
            "Keep irrigation off foliage during evening.",
            "Remove crop residue after harvest and rotate with non-host crops.",
        ],
        "visual_indicators": [
            "Long cigar-shaped grey-green or tan lesions.",
            "Lesions expanding after cloudy wet days.",
            "Loss of green leaf area on older leaves.",
        ],
        "preventive_measures": [
            "Rotate maize with non-host crops.",
            "Bury or remove infected residue after harvest where locally appropriate.",
            "Use resistant hybrids next season if disease pressure repeats.",
        ],
        "medicine_guidance": [
            "If upper canopy infection increases, ask for a locally registered maize blight fungicide.",
            "Follow label timing, dose, and worker-safety rules.",
        ],
        "fertilizer_guidance": [
            "Maintain balanced fertility to reduce stress.",
            "Do not rely on fertilizer to cure leaf blight.",
        ],
        "natural_remedies": [
            "Avoid wetting leaves in the evening.",
            "Remove infected residue after harvest.",
            "Improve airflow along dense crop edges.",
        ],
        "precautions": [
            "Scout upper canopy if weather remains humid.",
            "Seek local advice before applying fungicide.",
        ],
        "do_not": [
            "Do not rely on one-time scanning during wet weather.",
            "Do not move infected residue to healthy plots.",
        ],
        "next_check": [
            "Look for long cigar-shaped lesions.",
            "Check if lesions are moving from lower leaves upward.",
        ],
        "follow_up": "Rescan the same row in about 48 hours.",
    },
    ("rose", "black spot"): {
        "symptoms": [
            "Dark round leaf spots and yellowing leaves can suggest black spot.",
            "Lower leaves are often affected first.",
        ],
        "possible_causes": [
            "Fungal disease favored by humidity, shade, and wet leaves.",
        ],
        "recommendations": [
            "Remove spotted leaves and fallen leaves from around the plant.",
            "Water at soil level and improve airflow with careful pruning.",
            "Use locally recommended rose disease control only after confirming spread.",
        ],
        "visual_indicators": [
            "Dark round spots on rose leaves.",
            "Yellowing around spots.",
            "Lower leaves affected first.",
        ],
        "preventive_measures": [
            "Remove fallen leaves from around roses.",
            "Prune for airflow.",
            "Water soil, not leaves.",
        ],
        "medicine_guidance": [
            "If confirmed and spreading, ask for a rose-safe fungicide registered locally.",
            "Follow ornamental plant label instructions and avoid spraying during heat or wind.",
        ],
        "fertilizer_guidance": [
            "Use balanced rose fertilizer only for general plant health.",
            "Avoid pushing soft growth with excess nitrogen during disease pressure.",
        ],
        "natural_remedies": [
            "Remove infected leaves and fallen debris.",
            "Improve sunlight and airflow.",
            "Water at soil level in the morning.",
        ],
        "precautions": [
            "Avoid wetting leaves late in the day.",
            "Clean tools after pruning affected shoots.",
        ],
        "do_not": [
            "Do not leave infected fallen leaves under the rose.",
            "Do not apply strong chemical treatment without local label guidance.",
        ],
        "next_check": [
            "Photograph both affected and healthy leaves.",
            "Check whether spots have fringed dark margins.",
        ],
        "follow_up": "Rescan after pruning or sanitation in 3 to 5 days.",
    },
    ("rose", "powdery mildew"): {
        "symptoms": [
            "White powdery coating can appear on leaves, buds, or stems.",
            "New leaves may curl or distort.",
        ],
        "possible_causes": [
            "Fungal mildew favored by humid air and poor airflow.",
        ],
        "recommendations": [
            "Improve airflow around the plant.",
            "Remove badly affected leaves without over-pruning.",
            "Seek local rose-care guidance if mildew spreads to buds.",
        ],
        "visual_indicators": [
            "White powdery coating on leaves, buds, or stems.",
            "Curled or distorted young leaves.",
            "Symptoms on shaded, crowded growth.",
        ],
        "preventive_measures": [
            "Increase airflow through pruning.",
            "Avoid excessive nitrogen.",
            "Keep roses in good light where possible.",
        ],
        "medicine_guidance": [
            "If mildew spreads to buds, ask for a rose-safe mildew fungicide registered locally.",
            "Avoid spraying during hot sun and follow the label.",
        ],
        "fertilizer_guidance": [
            "Avoid nitrogen-heavy feeding while mildew is active.",
            "Use balanced rose nutrition only as routine care.",
        ],
        "natural_remedies": [
            "Remove the worst affected leaves.",
            "Improve airflow and sunlight.",
            "Avoid wetting foliage late in the day.",
        ],
        "precautions": [
            "Avoid excess nitrogen that encourages soft new growth.",
            "Keep leaves dry during evening watering.",
        ],
        "do_not": [
            "Do not crowd plants with poor airflow.",
            "Do not spray during hot sun or windy conditions.",
        ],
        "next_check": [
            "Inspect young leaves and buds for white coating.",
            "Photograph a close-up of affected growth tips.",
        ],
        "follow_up": "Rescan in 3 to 5 days after airflow and watering changes.",
    },
}


HEALTHY_KNOWLEDGE = {
    "symptoms": [
        "No disease-specific class was stronger than the healthy crop pattern.",
        "Continue using repeated scans to confirm the crop stays stable.",
    ],
    "possible_causes": ["No strong crop-specific disease signal was detected."],
    "recommendations": [
        "Continue routine scouting.",
        "Keep this scan as a baseline for future comparison.",
        "Rescan after rain, irrigation, or visible symptom changes.",
    ],
    "visual_indicators": [
        "The crop-specific healthy class was the strongest reliable match.",
        "No supported disease class was strong enough to report as the main problem.",
    ],
    "preventive_measures": [
        "Continue routine scouting twice a week.",
        "Keep leaves dry where possible.",
        "Maintain field sanitation and balanced watering.",
    ],
    "medicine_guidance": [
        "No medicine is suggested from this result.",
        "Do not spray unless clear pest or disease evidence appears.",
    ],
    "fertilizer_guidance": [
        "Continue your normal balanced nutrition plan.",
        "Do not add fertilizer as a reaction to a healthy scan.",
    ],
    "natural_remedies": [
        "Keep the field clean.",
        "Use this photo as a baseline for future scans.",
        "Monitor after rain or sudden weather changes.",
    ],
    "expert_confirmation": "Expert confirmation is not urgent unless symptoms appear or spread.",
    "precautions": GENERIC_PRECAUTIONS,
    "do_not": ["Do not apply pesticide without visible pest or disease evidence."],
    "next_check": GENERIC_NEXT_CHECK,
    "follow_up": "Run another scan during routine monitoring or if symptoms appear.",
}


def normalize(value):
    return (value or "").strip().lower().replace("_", " ")


def knowledge_for(crop_name, disease_name, is_healthy=False):
    if is_healthy or normalize(disease_name) == "healthy":
        return HEALTHY_KNOWLEDGE

    knowledge = DISEASE_KNOWLEDGE.get(
        (normalize(crop_name), normalize(disease_name)),
        {
            "symptoms": [
                "The model matched this crop-specific disease class, but direct symptom evidence is limited.",
                "Use the next scan to capture a closer view of affected tissue.",
            ],
            "possible_causes": [
                "Disease, pest damage, nutrient stress, water stress, or physical damage may still be possible.",
            ],
            "recommendations": [
                "Inspect several nearby plants for the same pattern.",
                "Remove only clearly damaged material and keep the area clean.",
                "Ask a local agriculture expert before applying chemical treatment.",
            ],
            "visual_indicators": DEFAULT_VISUAL_INDICATORS,
            "preventive_measures": DEFAULT_PREVENTION,
            "medicine_guidance": DEFAULT_MEDICINE_GUIDANCE,
            "fertilizer_guidance": DEFAULT_FERTILIZER_GUIDANCE,
            "natural_remedies": DEFAULT_NATURAL_REMEDIES,
            "expert_confirmation": DEFAULT_EXPERT_CONFIRMATION,
            "precautions": GENERIC_PRECAUTIONS,
            "do_not": GENERIC_AVOID,
            "next_check": GENERIC_NEXT_CHECK,
            "follow_up": "Rescan with a closer image in 2 to 3 days.",
        },
    )
    return {
        "symptoms": knowledge.get("symptoms", []),
        "possible_causes": knowledge.get("possible_causes", []),
        "recommendations": knowledge.get("recommendations", []),
        "visual_indicators": knowledge.get("visual_indicators", DEFAULT_VISUAL_INDICATORS),
        "preventive_measures": knowledge.get("preventive_measures", DEFAULT_PREVENTION),
        "medicine_guidance": knowledge.get("medicine_guidance", DEFAULT_MEDICINE_GUIDANCE),
        "fertilizer_guidance": knowledge.get("fertilizer_guidance", DEFAULT_FERTILIZER_GUIDANCE),
        "natural_remedies": knowledge.get("natural_remedies", DEFAULT_NATURAL_REMEDIES),
        "expert_confirmation": knowledge.get("expert_confirmation", DEFAULT_EXPERT_CONFIRMATION),
        "precautions": knowledge.get("precautions", GENERIC_PRECAUTIONS),
        "do_not": knowledge.get("do_not", GENERIC_AVOID),
        "next_check": knowledge.get("next_check", GENERIC_NEXT_CHECK),
        "follow_up": knowledge.get("follow_up", "Rescan with a closer image in 2 to 3 days."),
    }


def unsupported_crop_response(crop_name):
    return {
        "crop_name": crop_name,
        "diagnosis": "Insufficient visual evidence",
        "diagnosis_status": "inconclusive",
        "reliability": "Low",
        "model_confidence": None,
        "severity": "Unknown",
        "health_status": "Needs clearer evidence",
        "health_score": None,
        "evidence": [
            f"The trained PlantVillage disease model does not include crop-specific classes for {crop_name}.",
            "The image was saved as a crop observation, but disease prediction is not reliable for this crop yet.",
        ],
        "possible_causes": [
            "Disease, pest damage, nutrient stress, water stress, or physical damage could be involved.",
        ],
        "recommendations": [
            "Upload a closer photo of the affected leaf or plant part.",
            "Record when the symptom started and whether it is spreading.",
            "Seek local agricultural confirmation before applying treatment.",
        ],
        "visual_indicators": [],
        "preventive_measures": DEFAULT_PREVENTION,
        "medicine_guidance": [
            "No crop-specific medicine can be suggested because this crop is not supported by the current disease model.",
            "Ask a local agriculture expert before applying any chemical treatment.",
        ],
        "fertilizer_guidance": DEFAULT_FERTILIZER_GUIDANCE,
        "natural_remedies": DEFAULT_NATURAL_REMEDIES,
        "expert_confirmation": DEFAULT_EXPERT_CONFIRMATION,
        "description_alignment": "The farmer observation was saved, but model support for this crop is unavailable.",
        "top_predictions": [],
        "precautions": GENERIC_PRECAUTIONS,
        "do_not": GENERIC_AVOID,
        "next_check": GENERIC_NEXT_CHECK,
        "follow_up": "Add a close-up scan once crop-specific training support is available.",
        "model_label": "",
        "model_note": "Unsupported crop for the current disease model.",
    }
