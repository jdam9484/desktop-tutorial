"""Etiquetas de fauna y flora amazónica para CLIP (español -> inglés)."""
from apps.comun.vision import ZeroShot

ESPECIES = {
    "jaguar": "jaguar (Panthera onca), a spotted big cat", "ronsoco": "capybara",
    "guacamayo": "macaw parrot", "tucán": "toucan", "perezoso": "sloth", "mono": "monkey",
    "caimán": "caiman", "anaconda": "anaconda snake", "lobo de río": "giant river otter",
    "tapir": "tapir", "águila harpía": "harpy eagle", "rana": "poison dart frog",
    "mariposa": "butterfly", "oso hormiguero": "anteater", "shihuahuaco y árboles": "large rainforest tree",
    "orquídea": "orchid flower", "heliconia": "heliconia flower", "nenúfar gigante": "giant water lily Victoria amazonica",
    "castaña": "Brazil nut", "cacao": "cacao fruit pod", "palmera": "palm tree",
    "otro": "object, person, document or city scene",
}
PLANTILLAS = ["a photo of a {}.", "a photo of a {} in the Amazon rainforest.", "a close-up photo of a {}."]
clasificador = ZeroShot(ESPECIES, PLANTILLAS)
