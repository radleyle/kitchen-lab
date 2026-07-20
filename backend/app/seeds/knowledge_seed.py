"""Seed the food-science knowledge base: claim-sized, cited passages.

Run inside the container:
    docker compose exec backend python -m app.seeds.knowledge_seed
then embed the new passages:
    docker compose exec backend python -m app.rag.ingestion

Additively idempotent: sources are get-or-created by title, passages are
skipped if a passage with the same claim already exists. Safe to re-run
after every edit; only new passages are inserted (and only they will need
embedding, since their embedding column starts NULL).

Passages are paraphrased summaries of established food science, each tied
to the reference where the mechanism is documented, with an explicit scope
and an honest confidence level:
  high   = well-established mechanism, broad agreement
  medium = strong culinary consensus / tested practice
  low    = contested or context-dependent; presented with caveats
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import KnowledgeSource, SourcePassage

SOURCES = {
    "mcgee": {
        "title": "On Food and Cooking: The Science and Lore of the Kitchen",
        "author": "Harold McGee",
        "url": None,
        "source_type": "book",
        "authority_level": "science",
        "published_at": date(2004, 11, 23),
        "reviewed_at": date(2026, 7, 16),
    },
    "foodlab": {
        "title": "The Food Lab: Better Home Cooking Through Science",
        "author": "J. Kenji Lopez-Alt",
        "url": None,
        "source_type": "book",
        "authority_level": "culinary",
        "published_at": date(2015, 9, 21),
        "reviewed_at": date(2026, 7, 16),
    },
    "sfah": {
        "title": "Salt Fat Acid Heat: Mastering the Elements of Good Cooking",
        "author": "Samin Nosrat",
        "url": None,
        "source_type": "book",
        "authority_level": "culinary",
        "published_at": date(2017, 4, 25),
        "reviewed_at": date(2026, 7, 16),
    },
    "usda_fsis": {
        "title": "USDA FSIS Food Safety Fact Sheets",
        "author": "USDA Food Safety and Inspection Service",
        "url": "https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation",
        "source_type": "agency",
        "authority_level": "safety",
        "published_at": date(2020, 1, 1),
        "reviewed_at": date(2026, 7, 16),
    },
    "kingarthur": {
        "title": "King Arthur Baking: Learn -- Baking Guides",
        "author": "King Arthur Baking Company",
        "url": "https://www.kingarthurbaking.com/learn",
        "source_type": "article",
        "authority_level": "culinary",
        "published_at": date(2022, 1, 1),
        "reviewed_at": date(2026, 7, 16),
    },
    "seriouseats": {
        "title": "Serious Eats: Techniques",
        "author": "Serious Eats",
        "url": "https://www.seriouseats.com/cooking-techniques-5117399",
        "source_type": "article",
        "authority_level": "culinary",
        "published_at": date(2022, 1, 1),
        "reviewed_at": date(2026, 7, 16),
    },
    # Chef Fatty: one source record per article, so citations link to the
    # exact page. Authority level "culinary" -- tested practice, not a lab.
    "cf_velveting": {
        "title": "Velveting: Why Your Stir-Fry Chicken Is Always Dry (And the Two-Ingredient Fix)",
        "author": "Chef Fatty",
        "url": "https://www.cheffatty.com/science/why-chicken-gets-dry-stir-fry",
        "source_type": "article",
        "authority_level": "culinary",
        "published_at": date(2026, 4, 29),
        "reviewed_at": date(2026, 7, 16),
    },
    "cf_shrimp": {
        "title": "Why Your Shrimp Is Always Rubbery (And How to Fix It for Good)",
        "author": "Chef Fatty",
        "url": "https://www.cheffatty.com/science/why-your-shrimp-is-always-rubbery",
        "source_type": "article",
        "authority_level": "culinary",
        "published_at": date(2026, 5, 13),
        "reviewed_at": date(2026, 7, 16),
    },
    "cf_vinaigrette": {
        "title": "The Science of the Perfect Vinaigrette (And 4 Recipes That Prove It)",
        "author": "Chef Fatty",
        "url": "https://www.cheffatty.com/science/science-of-the-perfect-vinaigrette",
        "source_type": "article",
        "authority_level": "culinary",
        "published_at": date(2026, 6, 8),
        "reviewed_at": date(2026, 7, 16),
    },
    "pork_study": {
        "title": "Internal Endpoint Cooking Temperature Alters Quality and Consumer Acceptability of Pork Loin Chops (Foods, 2025)",
        "author": "MDPI Foods 14(12):2052",
        "url": "https://www.mdpi.com/2304-8158/14/12/2052",
        "source_type": "paper",
        "authority_level": "science",
        "published_at": date(2025, 6, 1),
        "reviewed_at": date(2026, 7, 16),
    },
    # H Woo Lee (hwoolee.com): elevated home cooking / "Cooking for Myself".
    # One source per article URL so citations deep-link. Culinary practice.
    "hwl_site": {
        "title": "H Woo Lee — Cooking for Myself (hwoolee.com)",
        "author": "H Woo Lee",
        "url": "https://www.hwoolee.com/",
        "source_type": "article",
        "authority_level": "culinary",
        "published_at": date(2024, 1, 1),
        "reviewed_at": date(2026, 7, 19),
    },
    "hwl_steakhouse_burger": {
        "title": "Owen Han's Steakhouse Burger",
        "author": "H Woo Lee",
        "url": "https://www.hwoolee.com/recipes/owen-hans-steakhouse-burger",
        "source_type": "article",
        "authority_level": "culinary",
        "published_at": date(2024, 1, 1),
        "reviewed_at": date(2026, 7, 19),
    },
    "hwl_bone_marrow_pappardelle": {
        "title": "Bone Marrow Pappardelle (H Woo Lee recipe published via Modern Luxury)",
        "author": "H Woo Lee",
        "url": "https://www.modernluxury.com/how-to-make-bone-marrow-pappardelle/",
        "source_type": "article",
        "authority_level": "culinary",
        "published_at": date(2022, 1, 1),
        "reviewed_at": date(2026, 7, 19),
    },
}

# (source_key, claim, content, scope, confidence)
PASSAGES = [
    # ================= MEAT TEXTURE AND BROWNING =================
    ("mcgee",
     "Muscle proteins squeeze out moisture as internal temperature rises past ~60C.",
     "As meat heats, its proteins denature and contract. Above roughly 60C the "
     "contracting protein network squeezes free water out of the muscle fibers; "
     "the higher the final temperature, the greater the moisture loss and the "
     "drier and firmer the result.",
     "Whole-muscle meats; timing varies by cut and species.",
     "high"),
    ("mcgee",
     "Browning (Maillard reaction) requires a hot, relatively dry surface.",
     "The Maillard reaction between amino acids and sugars produces browned "
     "flavors, and proceeds rapidly well above water's boiling point. While a "
     "meat surface is wet, evaporation holds surface temperature near 100C, "
     "delaying browning. Drying the surface before searing shortens the wait.",
     "Applies to searing/roasting; not deep frying where oil supplies heat.",
     "high"),
    ("foodlab",
     "Salting meat well before cooking improves moisture retention.",
     "Salt applied ahead of time first draws moisture out, then dissolves some "
     "surface proteins; the brine is reabsorbed and the loosened protein "
     "structure holds water better during cooking. Salting 45+ minutes ahead "
     "(or just before cooking) beats salting 5-30 minutes ahead, which leaves "
     "undissolved moisture at the surface and hampers searing.",
     "Steaks and chops; tested for pre-salting timing.",
     "medium"),
    ("foodlab",
     "Slicing meat against the grain shortens muscle fibers and reads as tenderness.",
     "Muscle fibers run in bundles along a visible grain. Cutting perpendicular "
     "to the grain shortens each fiber segment so the teeth sever less; the "
     "same cut sliced with the grain chews noticeably tougher.",
     "Especially significant for long-fibered cuts like flank or skirt steak.",
     "high"),
    ("mcgee",
     "A baking-soda surface treatment raises pH and helps keep thin-sliced meat tender.",
     "Raising the surface pH of meat with a small amount of baking soda "
     "increases protein charge and water retention and hinders protein bonding "
     "during cooking, keeping thin slices springy and tender. Excess soda "
     "leaves a soapy, bitter taste and slick texture, so quantity and timing "
     "matter; rinsing removes residue.",
     "Thin-sliced meats for stir-frying (velveting); not whole roasts.",
     "medium"),
    ("mcgee",
     "Slow, moist cooking converts collagen to gelatin and tenderizes tough cuts.",
     "Connective tissue's collagen dissolves into gelatin with time at "
     "temperatures above about 70C. Tough, well-exercised cuts (shank, chuck, "
     "brisket) become succulent after hours of braising because gelatin "
     "lubricates the fibers, even as the muscle itself loses moisture.",
     "Collagen-rich cuts; lean tender cuts only dry out with this treatment.",
     "high"),
    ("foodlab",
     "Resting cooked meat before slicing reduces juice loss, but the effect is debated.",
     "Cutting meat straight off the heat spills more juices onto the board "
     "than cutting after a short rest, as the temperature and pressure "
     "gradients relax. However, controlled tests suggest the total difference "
     "is smaller than folklore claims, and a rest also causes carryover "
     "cooking. A brief rest is cheap insurance, not magic.",
     "Steaks and roasts; the size of the benefit is contested.",
     "low"),
    ("foodlab",
     "Carryover cooking: internal temperature keeps rising after meat leaves the heat.",
     "The hot exterior continues conducting heat inward after cooking stops, "
     "raising the center by roughly 3-10C depending on size and cooking "
     "temperature. Large roasts cooked at high heat carry over the most. "
     "Pulling meat below the target temperature accounts for it.",
     "All roasted/seared meats; magnitude varies with mass and method.",
     "high"),
    ("foodlab",
     "The reverse sear: gentle heat first, hard sear last, evens doneness.",
     "Cooking a thick steak at low temperature first brings the interior "
     "evenly to target, dries the surface (aiding browning), then a brief "
     "very hot sear builds crust without a thick gray overcooked band. The "
     "traditional hard-sear-first approach creates steeper gradients.",
     "Thick steaks and roasts (about 4cm+); pointless for thin cuts.",
     "medium"),
    ("mcgee",
     "Marinades penetrate meat very slowly; most flavor stays at the surface.",
     "Flavor molecules in marinades migrate into meat on the order of "
     "millimeters per day; overnight marinating flavors mainly the exterior. "
     "Salt (and thin cuts or scoring) are the exceptions that meaningfully "
     "change interior seasoning.",
     "All meats; salt-based brines behave differently from flavor marinades.",
     "high"),
    ("mcgee",
     "Prolonged acidic marinades turn the meat surface mushy, not tender.",
     "Strong acid denatures surface proteins into a soft, mealy layer while "
     "leaving the interior unchanged. Brief acid contact brightens flavor; "
     "hours of it degrade texture. Enzymatic tenderizers (papaya's papain, "
     "pineapple's bromelain) similarly over-soften the surface with time.",
     "Acid- or enzyme-heavy marinades; dairy-based marinades are gentler.",
     "high"),
    ("seriouseats",
     "Crowding the pan causes steaming instead of browning.",
     "Each piece of cold food releases moisture as it heats. Too many pieces "
     "at once overwhelm the pan's heat and trap steam between them, holding "
     "the surface near 100C -- food stews gray in its own juices. Cook in "
     "batches with space, and browning resumes.",
     "Stovetop searing and sauteing; also roasting on crowded sheet pans.",
     "high"),
    ("usda_fsis",
     "Color is not a reliable doneness indicator; only temperature is.",
     "Ground beef can turn brown before reaching a safe temperature, and "
     "safely cooked poultry can remain pink near the bone. Pigment chemistry "
     "varies with pH, packaging, and age, so visual color misleads in both "
     "directions. A thermometer in the thickest part is the only reliable check.",
     "All meats; especially critical for ground meat and poultry.",
     "high"),
    ("foodlab",
     "Sous vide holds food at an exact temperature, decoupling doneness from timing.",
     "A water bath at the target temperature cannot overcook food the way a "
     "pan or oven (far hotter than the target) can. Doneness becomes a "
     "temperature choice and tenderness a time choice, at the cost of no "
     "browning -- a hard sear afterward adds the crust.",
     "Vacuum-sealed foods in a circulated bath; requires safe time-temperature combinations.",
     "high"),

    # ================= SAUCES, STARCHES, EMULSIONS =================
    ("mcgee",
     "Starch thickens liquids by gelatinization between roughly 60-95C.",
     "Heated in water, starch granules absorb water and swell (gelatinization), "
     "leaking amylose that thickens the liquid. Different starches gelatinize "
     "over different ranges and give different textures: root starches like "
     "potato and tapioca thicken at lower temperatures and turn clearer and "
     "more elastic; grain starches like corn and wheat give opaque, softer gels.",
     "Water-based liquids; sugar and acid shift the temperatures.",
     "high"),
    ("mcgee",
     "Overheating or over-stirring can thin a starch-thickened sauce.",
     "After gelatinization, prolonged boiling or vigorous stirring ruptures "
     "swollen starch granules and the sauce thins irreversibly. Root starches "
     "are more fragile than corn starch; add them near the end of cooking.",
     "Most visible with potato/tapioca starch.",
     "high"),
    ("mcgee",
     "Emulsions break when fat is added faster than it can be dispersed.",
     "An emulsion holds tiny oil droplets separated by emulsifiers. Adding fat "
     "too quickly, or overheating, lets droplets merge and the sauce splits. "
     "Adding fat gradually with constant agitation, and moderating heat, keeps "
     "droplets small and the emulsion stable; a broken emulsion can often be "
     "rescued by whisking it slowly into a fresh base with more emulsifier.",
     "Butter sauces, mayonnaise, hollandaise, vinaigrettes.",
     "high"),
    ("foodlab",
     "Cornstarch in a velveting slurry forms a protective coating, not a tenderizer.",
     "A cornstarch coating on thin-sliced meat gelatinizes into a thin sheath "
     "during brief cooking. The sheath buffers the meat from direct heat and "
     "slows moisture loss -- the slices stay juicy. The starch itself does not "
     "break down muscle fiber; tenderizing comes from slicing, marinade, or pH.",
     "Stir-fry velveting with brief, hot cooking.",
     "medium"),
    ("mcgee",
     "A darker roux tastes nuttier but thickens less.",
     "Toasting flour in fat (a roux) breaks starch chains as it browns: white "
     "and blond roux thicken strongly with neutral flavor, while brown and "
     "dark roux trade much of their thickening power for deep toasted flavor. "
     "Dark-roux dishes therefore need more roux or another thickener.",
     "Flour-based roux; ratio guidance differs by target thickness.",
     "high"),
    ("seriouseats",
     "Slurries thicken instantly at a simmer; roux needs cooking to lose rawness.",
     "A cold starch slurry (starch whisked into cold water) can be stirred "
     "into a simmering liquid at the end and thickens within a minute. Flour "
     "roux must cook long enough to lose its raw cereal taste. Slurries suit "
     "quick fixes and glossy Asian-style sauces; roux suits built-in body.",
     "Everyday sauce thickening; pastry creams differ.",
     "medium"),
    ("mcgee",
     "Egg yolk's lecithin and proteins make it a powerful emulsifier.",
     "Yolk contains phospholipids (notably lecithin) and proteins that coat "
     "oil droplets and keep them from merging, which is why mayonnaise and "
     "hollandaise can hold remarkable amounts of fat in a stable cream. One "
     "yolk can emulsify far more oil than intuition suggests; failure usually "
     "comes from speed or temperature, not capacity.",
     "Egg-based emulsions.",
     "high"),
    ("mcgee",
     "Tempering eggs prevents curdling when combining them with hot liquids.",
     "Egg proteins coagulate quickly above ~70-80C. Whisking a little hot "
     "liquid into the eggs first raises their temperature gradually, diluting "
     "and warming the proteins so they thicken smoothly instead of scrambling "
     "when the mixtures are combined.",
     "Custards, pastry cream, carbonara, egg-thickened soups.",
     "high"),
    ("mcgee",
     "Starch-thickened mixtures set thicker as they cool (retrogradation).",
     "After gelatinization, dissolved starch molecules re-associate on "
     "cooling, tightening the network: a sauce that looks right at a simmer "
     "may set too thick cold, and a pie filling thin at the boil firms as it "
     "cools. Judge starch dishes at their serving temperature. The same "
     "process firms day-old bread (staling).",
     "All starch-thickened preparations; strongest with grain starches.",
     "high"),
    ("seriouseats",
     "Cheese sauces break without emulsifying salts or starch protection.",
     "Cheese is itself an emulsion of fat in a protein matrix; direct heat "
     "separates it into grease and curds. A starch-thickened base (bechamel) "
     "physically stabilizes the melt, while sodium citrate raises pH and "
     "frees casein to act as the emulsifier -- the smooth-melt trick behind "
     "processed cheese and modern mac and cheese.",
     "Melted cheese sauces; aged/dry cheeses break most readily.",
     "medium"),
    ("sfah",
     "Reduction thickens and intensifies, but concentrates salt too.",
     "Simmering a sauce evaporates water, concentrating both body and every "
     "dissolved flavor -- including salt. Season reductions at the end: a "
     "correctly salted liquid reduced by half becomes twice as salty.",
     "Reduced sauces, stocks, and braising liquids.",
     "high"),
    ("mcgee",
     "Gelatin from bones and connective tissue gives stocks body.",
     "Long-simmered bones and cartilage release gelatin, which thickens stock "
     "subtly and gives sauces a silky, mouth-coating body that water-thin "
     "broths lack; chilled, a gelatin-rich stock sets to a jelly. Pressure "
     "cookers extract gelatin faster at higher temperature.",
     "Meat and poultry stocks; vegetable stocks have no gelatin.",
     "high"),
    ("seriouseats",
     "Mounting butter into a sauce (monter au beurre) adds gloss and body.",
     "Whisking cold butter cubes into a warm sauce off the heat disperses "
     "butterfat as fine droplets in a fragile emulsion, adding sheen, body, "
     "and richness. Overheating afterward breaks it -- finish just before "
     "serving and keep the sauce below a simmer.",
     "Pan sauces and reductions, added at the end.",
     "medium"),
    ("mcgee",
     "Deglazing dissolves the browned fond into the sauce.",
     "The browned residue stuck to a pan after searing (fond) is concentrated "
     "Maillard flavor. Adding liquid to the hot pan and scraping dissolves it "
     "into the base of a pan sauce; skipping deglazing discards much of the "
     "flavor the sear created.",
     "Pan sauces after searing; nonstick pans build little fond.",
     "high"),

    # ================= BAKING TEXTURE =================
    ("mcgee",
     "Gluten develops when wheat flour proteins hydrate and are worked.",
     "Wheat's glutenin and gliadin link into an elastic gluten network when "
     "hydrated and kneaded. More water, more mixing, and more time mean more "
     "gluten: desirable for chewy bread, undesirable for tender cakes and "
     "pastry, which is why those recipes minimize mixing once flour is wet.",
     "Wheat flours; rye and others behave differently.",
     "high"),
    ("foodlab",
     "Butter temperature controls cookie spread.",
     "Cookies made with warm or melted butter spread thin because the fat "
     "liquefies before the structure sets; cold or chilled dough spreads less. "
     "Chilling dough also allows flour hydration and flavor development. "
     "Higher sugar ratios and less flour also increase spread.",
     "Drop cookies (e.g. chocolate chip).",
     "medium"),
    ("mcgee",
     "Baking soda needs an acid to leaven; baking powder brings its own.",
     "Baking soda (sodium bicarbonate) releases carbon dioxide only when it "
     "meets acid and moisture. Baking powder packages the soda with a dry acid, "
     "activating on wetting and again on heating (double-acting). Substituting "
     "one for the other changes both rise and browning: soda raises pH, which "
     "speeds Maillard browning and can taste soapy in excess.",
     "Chemical leavening in quick breads, cookies, cakes.",
     "high"),
    ("kingarthur",
     "Flour protein content sets the texture ceiling: bread vs all-purpose vs cake.",
     "Higher-protein bread flour (~12-14%) builds more gluten for chew and "
     "structure; cake flour (~7-9%) builds less, for tenderness; all-purpose "
     "sits between. Swapping flours changes hydration needs and texture even "
     "when the recipe otherwise stays the same.",
     "Wheat flours in yeast breads, cakes, and pastry.",
     "high"),
    ("mcgee",
     "Sugar tenderizes and keeps baked goods moist, beyond sweetening.",
     "Sugar competes with flour proteins and starch for water, limiting gluten "
     "development and slowing starch setting -- more sugar means more tender, "
     "moister crumb and more spread. Sugar is also hygroscopic, holding "
     "moisture so high-sugar bakes stay soft days longer.",
     "Cookies, cakes, quick breads; artificial sweeteners do not behave the same.",
     "high"),
    ("kingarthur",
     "Brown sugar makes chewier, moister cookies than white sugar.",
     "Brown sugar's molasses adds moisture and acidity: the extra moisture "
     "and hygroscopic fructose keep cookies soft and chewy, while the acidity "
     "activates baking soda for lift and speeds browning. All-white-sugar "
     "cookies bake crisper and spread with sharper edges.",
     "Drop cookies; effects scale with the brown:white ratio.",
     "medium"),
    ("sfah",
     "Creaming butter and sugar aerates the dough; those bubbles are the leavening seed.",
     "Beating room-temperature butter with sugar cuts millions of tiny air "
     "pockets into the fat. Chemical leaveners and steam later inflate these "
     "existing bubbles -- they cannot create new ones -- so under-creamed "
     "batter bakes denser regardless of how much baking powder it contains.",
     "Creamed-batter cakes and cookies; melted-fat recipes skip this entirely.",
     "high"),
    ("mcgee",
     "Eggs provide structure, moisture, emulsification, and lift -- know which job matters.",
     "Egg proteins coagulate to set crumb structure; yolks carry fat and "
     "lecithin that emulsify and tenderize; whites can be whipped into a foam "
     "that leavens. A substitution that works when the egg binds (flax gel) "
     "fails when the egg must foam (angel food). Identify the egg's function "
     "in the recipe before replacing it.",
     "Baking substitutions; function determines the viable replacement.",
     "high"),
    ("kingarthur",
     "Overmixed muffin and pancake batter turns tough and tunneled.",
     "Once flour is wet, every stir builds gluten. Quick-bread batters should "
     "be mixed only until the dry streaks disappear -- lumps are fine. "
     "Overmixing yields rubbery texture and elongated interior tunnels as "
     "gas escapes through a tightened gluten network.",
     "Muffins, pancakes, quick breads; not yeast doughs, which want gluten.",
     "high"),
    ("kingarthur",
     "Weighing ingredients beats volume measuring for consistency.",
     "A 'cup of flour' varies by 20-30% depending on scooping, settling, and "
     "humidity -- enough to swing a dough from slack to stiff. A scale removes "
     "that variance entirely, which is why professional formulas are written "
     "in weight (and baker's percentages).",
     "All baking; most critical for flour and doughs.",
     "high"),
    ("seriouseats",
     "An autolyse rest builds gluten without kneading.",
     "Mixing just flour and water and resting 20-60 minutes lets enzymes and "
     "hydration begin developing gluten passively. Dough after autolyse "
     "kneads faster, extends more easily, and often bakes with better volume "
     "-- effort replaced by time.",
     "Yeast breads; salt and yeast are typically added after the rest.",
     "medium"),
    ("mcgee",
     "Yeast fermentation temperature trades speed for flavor.",
     "Warm dough (27-32C) ferments fast but accumulates less flavor; cool, "
     "slow fermentation (as in overnight refrigeration) lets enzymes and "
     "bacteria produce more complex flavors and better keeping quality. Same "
     "yeast, different clock, different bread.",
     "Yeast doughs; sourdough adds its own acid dynamics.",
     "high"),
    ("seriouseats",
     "Steam in the early bake maximizes oven spring and crust.",
     "A humid oven keeps the loaf's surface flexible during the first minutes "
     "of oven spring so it can expand fully, then gelatinizes surface starch "
     "for a glossy, crisp crust. Dry ovens set the crust early, limiting "
     "volume -- the reason home bakers use dutch ovens to trap steam.",
     "Lean crusty breads; enriched soft breads don't want it.",
     "medium"),
    # ================= CHEF FATTY + RELATED (added July 2026) =================
    ("cf_velveting",
     "Velveting dosage: about 1/4 tsp baking soda per pound of chicken, 15-20 minute rest, then rinse.",
     "For 450 g (1 lb) of thin-sliced chicken, toss with roughly 1/4 tsp baking "
     "soda and rest 15-20 minutes (up to 1 hour refrigerated). Rinse thoroughly "
     "under cold water and pat dry -- skipping the rinse leaves a metallic, "
     "soapy taste. The tenderizing has already happened by then; rinsing does "
     "not undo it. Coat with cornstarch and seasoning only after drying.",
     "Thin-sliced chicken for stir-frying; quantities scale linearly.",
     "medium"),
    ("cf_velveting",
     "Velveting transfers to beef, pork, and shrimp with adjusted dosage.",
     "The baking-soda-then-cornstarch sequence works on beef, pork, and shrimp. "
     "Shrimp protein is more delicate: use about half the baking soda (1/8 tsp "
     "per pound) and a shorter 10-15 minute rest, or the texture goes mushy "
     "instead of plump.",
     "Thin-cut or small pieces destined for hot, fast cooking.",
     "medium"),
    ("cf_shrimp",
     "Shrimp overcooks far below the color change: proteins set around 120F, pink appears around 140F.",
     "Shrimp proteins begin setting near 120F (49C), and texture stiffens "
     "steadily from there -- but the pink 'done' color only appears around "
     "140F (60C). Waiting for full pink means the shrimp has already tightened "
     "well past its best texture. Color is a lagging indicator; use shape or a "
     "thermometer instead. The FDA-safe endpoint for shellfish is 145F (62.8C), "
     "so moisture-protecting technique (brief high heat, starch coating) "
     "matters more for shrimp than almost any other protein.",
     "Shrimp cooked by any dry or wet heat; safe endpoint per FDA/USDA is 145F.",
     "medium"),
    ("cf_shrimp",
     "Shrimp shape signals doneness in real time: pull at a J-curve; a tight C is overcooked.",
     "Raw shrimp holds a gentle open curve. As proteins contract during "
     "cooking, the curve tightens: a relaxed J shape indicates just-set "
     "proteins with moisture intact -- the moment to pull -- while a tight C "
     "shape means the shrimp has fully contracted and squeezed out its juices. "
     "The J-to-C transition happens in seconds, faster than color changes.",
     "Whole shrimp cooked in shell or peeled; visual cue, not a safety check.",
     "medium"),
    ("cf_vinaigrette",
     "A stable vinaigrette follows roughly 9:3:1 -- oil : acid : emulsifier.",
     "One part concentrated emulsifier can hold about nine parts oil and three "
     "parts acid in a stable emulsion. Dijon mustard is the classic emulsifier "
     "because mustard-seed mucilage (a sticky polysaccharide) plus seed "
     "proteins coat oil droplets efficiently at small doses; whole-grain "
     "mustard, egg yolk, tahini, miso, or roasted garlic puree fill the same "
     "role with different flavors. Without an emulsifier, oil and vinegar "
     "separate within minutes and dress the salad unevenly.",
     "Vinaigrettes and cold emulsified dressings; ratio is a starting point to adjust by taste.",
     "medium"),
    ("pork_study",
     "Pork chops cooked to 63C (145F) measurably beat higher endpoints on juiciness and tenderness.",
     "In a controlled study of 264 pork loin chops cooked to 63C, 71C, or 79C, "
     "the 63C chops retained more moisture, had lower shear force (more "
     "tender), and won consumer panel ratings for juiciness, texture, and "
     "tenderness. The USDA lowered its whole-cut pork recommendation from "
     "160F to 145F (63C) plus a 3-minute rest in 2011; cooking pork to the "
     "old 160F standard is a primary cause of dry chops. Pink interior at "
     "145F is normal and safe.",
     "Whole-muscle pork chops and loins; ground pork still requires 160F.",
     "high"),
    ("mcgee",
     "Starch gelatinization and protein set, not browning, decide when the crumb is done.",
     "A loaf or cake is structurally done when its interior starch has "
     "gelatinized and proteins have set -- typically 90-99C internally "
     "depending on the bake. Surface color alone misleads: a dark crust can "
     "hide a gummy center. An instant-read thermometer settles it.",
     "Breads and cakes; target temperature varies by style.",
     "high"),
    # ================= H WOO LEE / hwoolee.com (added July 2026) =================
    ("hwl_site",
     "H Woo Lee teaches restaurant-caliber technique scaled for cooking for yourself at home.",
     "H Woo Lee's site (hwoolee.com) and Cooking for Myself series focus on "
     "bringing fine-dining moves -- arrosé basting, sauce reductions to nappe, "
     "careful fat work, fermented pantry flavors -- into a solo home kitchen. "
     "The teaching style is procedural and sensory (what to listen for and look "
     "for), not restaurant brigade scale.",
     "Home cooks adapting restaurant techniques; not a food-safety authority.",
     "medium"),
    ("hwl_steakhouse_burger",
     "Salt ground-beef patties only right before cooking so salt does not loosen the mix.",
     "On thick steakhouse-style burgers, H Woo Lee holds salt until the pan is "
     "hot and cooking is about to start. Salt dissolves muscle proteins and "
     "pulls free water; if that happens while the patty sits, the grind can "
     "loosen and steam instead of sear. Season both faces immediately before "
     "they hit the pan.",
     "Loose ground-beef or dry-aged beef patties formed ahead; not a rule for "
     "dry-brined whole steaks.",
     "medium"),
    ("hwl_steakhouse_burger",
     "Baste a burger like a steak: after the flip, spoon butter, bone marrow, garlic, and thyme over the patty.",
     "After searing the first side, flip the patty, lower to medium, and add "
     "butter, diced bone marrow, smashed garlic, and thyme. Spoon the melting "
     "fats repeatedly over the top (arrosé). The marrow and butter baste "
     "builds a steakhouse crust and flavor while the second side finishes -- "
     "treating the burger as a thick steak, not a thin smash.",
     "Thick (about 1/2 lb) pan-seared patties; needs rendered fat in the pan.",
     "medium"),
    ("hwl_steakhouse_burger",
     "A lid plus residual heat makes a mini oven that finishes thick burgers without a raw center.",
     "After basting, lay cheese on the patty, cover the pan, and turn the heat "
     "off for 2-3 minutes. Trapped steam and residual heat cook the thick "
     "center through to medium while melting the cheese -- essential because "
     "a hard sear alone often leaves a thick burger underdone inside.",
     "Thick pan burgers aiming for medium; still verify safety with a "
     "thermometer for ground beef (USDA 160F / 71C if following agency guidance).",
     "medium"),
    ("hwl_steakhouse_burger",
     "Reduce pan sauces to nappe (coats a spoon) before mounting cream or mayo.",
     "For the au poivre mayo base, H Woo Lee reduces shallot-pepper-cognac "
     "stock until nappe -- thick enough to coat the back of a spoon -- then "
     "adds cream and reduces to nappe again before cooling and folding into "
     "mayonnaise. Hitting nappe twice concentrates flavor and keeps the final "
     "mayo from turning watery.",
     "Peppercorn / pan reductions destined for cold emulsified sauces.",
     "medium"),
    ("hwl_steakhouse_burger",
     "For home grinding, freeze grinder parts and grind on a medium die for a steakhouse patty.",
     "When grinding your own blend, freeze the grinder attachments first and "
     "grind on a medium die. Cold metal keeps fat solid so it cuts cleanly "
     "instead of smearing; a medium die gives a steakhouse bite rather than "
     "a paste.",
     "Home-ground beef blends for thick burgers.",
     "medium"),
    ("hwl_bone_marrow_pappardelle",
     "Soak split marrow bones overnight in salted water to draw out blood and impurities before roasting.",
     "H Woo Lee's bone marrow prep starts with an overnight fridge soak: "
     "dissolve fine salt in water, submerge split femur bones, and chill. "
     "The brine pulls blood and impurities from the marrow cavities so the "
     "roast tastes clean rather than metallic. Drain, dry, oil, season, then "
     "roast hot (about 450F / 232C) until the marrow is soft and spoonable.",
     "Split beef marrow bones for roasting into pasta or toast; not a "
     "food-safety kill step by itself.",
     "medium"),
    ("hwl_bone_marrow_pappardelle",
     "Red wine in fresh pasta dough tints and flavors the sheets before the sauce even starts.",
     "For red-wine pappardelle, wine joins the wet mix (eggs, oil, wine) before "
     "the flour -- staining the dough and carrying Cabernet notes into every "
     "strand. The pasta itself becomes part of the wine story, not only the "
     "pan sauce later.",
     "Fresh egg pasta where a tinted, wine-scented dough is the goal.",
     "medium"),
]


def get_or_create_source(db: Session, key: str) -> KnowledgeSource:
    data = SOURCES[key]
    source = db.scalar(
        select(KnowledgeSource).where(KnowledgeSource.title == data["title"])
    )
    if source is None:
        source = KnowledgeSource(**data)
        db.add(source)
        db.flush()
    return source


def run(db: Session) -> str:
    sources = {key: get_or_create_source(db, key) for key in SOURCES}

    added = 0
    for source_key, claim, content, scope, confidence in PASSAGES:
        exists = db.scalar(select(SourcePassage).where(SourcePassage.claim == claim))
        if exists is not None:
            continue
        db.add(
            SourcePassage(
                source_id=sources[source_key].id,
                claim=claim,
                content=content,
                scope=scope,
                confidence=confidence,
            )
        )
        added += 1

    db.commit()
    return f"Added {added} new passages ({len(PASSAGES)} total in seed file)."


if __name__ == "__main__":
    with SessionLocal() as session:
        print(run(session))
