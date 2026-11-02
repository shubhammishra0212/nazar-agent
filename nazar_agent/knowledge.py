"""What each machine state means on the NAZAR line, and what to do about it.

This is the engineering knowledge of the 8D: the statistics say WHICH sensor state goes
with rejects, this file says what that state usually means on a small washer conveyor
(loose mount, dim light, overload, friction) and what maintenance should do.

Texts here carry no numbers on purpose: every number in a report comes from the statistics.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Factor:
    key: str        # field name in the inspection log (contract section 6)
    side: str       # "high": bad when ABOVE amber; "low": bad when BELOW amber (light)
    unit: str
    dec: int        # decimals when the limit is printed
    amber: float    # default limits, used only when the request has none
    red: float


FACTORS = [
    Factor("vib", "high", "g", 3, 0.08, 0.15),
    Factor("lux", "low", "lx", 0, 300, 120),
    Factor("temp", "high", "°C", 1, 45, 60),
    Factor("ma", "high", "mA", 0, 700, 1000),
]
BY_KEY = {f.key: f for f in FACTORS}

SECTION_TITLES = {
    "en": {"D1": "Team", "D2": "Problem", "D3": "Containment", "D4": "Root cause",
           "D5": "Corrective action", "D6": "Implement and verify", "D7": "Prevent recurrence",
           "D8": "Close and recognise"},
    "hi": {"D1": "टीम", "D2": "समस्या", "D3": "तुरंत रोकथाम", "D4": "मूल कारण",
           "D5": "सुधार की कार्रवाई", "D6": "लागू करना और जाँच", "D7": "दोबारा न हो",
           "D8": "समापन"},
}

# key None = no machine state explains the rejects
TEXT = {
    "en": {
        "vib": {
            "label": "Motor shaking",
            "state": "the motor was shaking above its amber limit",
            "title": "Rejects rise when the motor shakes",
            "fault": "a loose motor mount or a wobbling belt",
            "cause": "The belt motor's mount has worked loose (or the belt wobbles on its rollers), so the motor "
                     "shakes the belt and the washers riding on it.",
            "why": [
                "Why were more washers rejected? Most of the extra rejects came while the motor was shaking.",
                "Why does shaking cause rejects? A shaking belt tilts and shifts washers under the camera and knocks "
                "them against the guides, so the picture shows blur and scuff marks.",
                "Why is the motor shaking? Its mount has worked loose, or the belt is wobbling on the rollers.",
                "Why did the mount work loose? Constant vibration slowly backs off screws that have no thread-locker "
                "or spring washer.",
                "Why was it not caught earlier? The mount is not on a regular checklist and the amber shaking alarm "
                "was not acted on.",
            ],
            "contain": "Keep every washer going through the camera and check held washers by hand. If shaking stays "
                       "amber, stop the belt and check the motor mount before running more washers.",
            "act": "Stop the belt, tighten the motor mount screws and add thread-locker or spring washers. Check that "
                   "the belt runs straight and is evenly tensioned on the rollers. Restart and watch the shaking "
                   "reading fall back below amber.",
            "prevent": "Treat amber shaking as a stop-and-check signal. Add the motor mount screws and belt tracking "
                       "to the start-of-shift checklist. Re-learn the normal shaking level after any repair.",
        },
        "lux": {
            "label": "Low light",
            "state": "the tunnel light was below its amber limit",
            "title": "Rejects rise when the tunnel light is low",
            "fault": "a dim or failing tunnel LED, or a dirty diffuser",
            "cause": "The light in the camera tunnel drops (a dim or flickering LED strip, a loose connector or a dirty "
                     "diffuser), so the picture is too dark and good washers stop looking like the good ones the AI "
                     "learned.",
            "why": [
                "Why were more washers rejected? Most of the extra rejects came while the tunnel light was low.",
                "Why does low light cause rejects? In a dark picture a good washer looks different from the good "
                "washers the AI learned, so it scores as unusual.",
                "Why is the light low? The tunnel LED strip is dimming or flickering, or the diffuser is dirty.",
                "Why does the LED dim? A loose connector, a sagging supply voltage or dust on the diffuser cuts the "
                "light.",
                "Why was it not caught earlier? The tunnel light is not checked at the start of a shift and the amber "
                "light alarm was not acted on.",
            ],
            "contain": "Check held washers by hand. If the light stays amber, pause inspection and fix the light before "
                       "running more washers, because the AI cannot judge in the dark.",
            "act": "Clean the diffuser and the camera lens. Check the LED strip connector and its supply voltage. "
                   "Replace the LED strip if it stays dim. Keep the camera exposure locked so the picture does not drift.",
            "prevent": "Add the tunnel light reading and a lens wipe to the start-of-shift checklist. Treat amber light "
                       "as a stop-and-check signal. Keep a spare LED strip at the line.",
        },
        "temp": {
            "label": "Motor hot",
            "state": "the motor was running above its amber temperature",
            "title": "Rejects rise when the motor runs hot",
            "fault": "an overloaded motor",
            "cause": "The belt motor is overloaded and runs hot, so belt speed sags and surges and washers arrive under "
                     "the camera out of place.",
            "why": [
                "Why were more washers rejected? Most of the extra rejects came while the motor was hot.",
                "Why does a hot motor cause rejects? An overloaded motor slows and surges, so washers slip and stop "
                "off-centre under the camera.",
                "Why is the motor hot? It is overloaded: the belt is too tight, a roller drags or the duty is too heavy.",
                "Why was the extra load not noticed? Motor current and temperature were not watched together.",
                "Why was it not caught earlier? Belt tension, free-running rollers and motor cooling are not on a "
                "regular checklist.",
            ],
            "contain": "Check held washers by hand. If the temperature stays amber, stop the belt and let the motor cool "
                       "before running more washers.",
            "act": "Stop the belt and let the motor cool. Find the extra load: an over-tight belt, a stiff roller bearing "
                   "or debris. Remove it, set the belt tension correctly and make sure air can reach the motor.",
            "prevent": "Treat amber motor temperature as a stop-and-check signal. Check belt tension and that every "
                       "roller turns freely each shift. Keep the motor's air path clear.",
        },
        "ma": {
            "label": "Motor strain",
            "state": "the belt motor current was above its amber limit",
            "title": "Rejects rise when the belt motor strains",
            "fault": "belt friction or a jam",
            "cause": "The belt is rubbing or parts are catching (friction or a jam), so the motor draws extra current and "
                     "washers drag, get scuffed and reach the camera out of place.",
            "why": [
                "Why were more washers rejected? Most of the extra rejects came while the motor current was high.",
                "Why does high current go with rejects? When the belt drags, washers catch on the guides and get "
                "scuffed or stop off-centre under the camera.",
                "Why does the belt drag? It rubs on the frame or the guides, or debris is jammed in a roller.",
                "Why does that happen? Belt tracking drifts and debris builds up over a shift.",
                "Why was it not caught earlier? Belt tracking and guide clearance are not checked regularly and the "
                "amber current alarm was not acted on.",
            ],
            "contain": "Check held washers by hand. If the current stays amber, stop the belt and clear any jam before "
                       "running more washers.",
            "act": "Stop the belt, clear debris and free the guides. Re-track the belt so it runs straight without "
                   "rubbing. Check that every roller turns freely.",
            "prevent": "Treat amber motor current as a stop-and-check signal. Check belt tracking and guide clearance "
                       "each shift. Keep the line clean of washer debris.",
        },
        None: {
            "label": "No machine cause",
            "title": "No machine cause found: defects likely arrive with the washers",
            "fault": "the incoming washers",
            "cause": "No machine sensor explains the rejects: the reject rate is about the same whether the motor "
                     "shakes, runs hot or strains, or the light is low. The defects most likely come with the washers "
                     "themselves (incoming material or the previous process), or from something the sensors do not "
                     "measure.",
            "why": [
                "Why were washers rejected? The camera found real marks or shape faults on them.",
                "Why do the faults not follow the machine? The reject rate stays about the same in every machine state "
                "we measured.",
                "So is the line damaging the washers? Probably not; they most likely arrive with the faults.",
                "Where do the faults come from? Most likely the incoming batch or the process before this station.",
                "Why was it not caught earlier? Incoming washers are not sampled before they reach the line.",
            ],
            "contain": "Set the current batch aside, check a sample of held and rejected washers by hand, and keep every "
                       "washer going through the camera.",
            "act": "Check a hand sample of the current batch. Look through the rejected washers' pictures in NAZAR for "
                   "one common defect. Send the evidence to the supplier or the previous station.",
            "prevent": "Sample every new batch before it goes on the line. Review the NAZAR defect trend each shift. "
                       "Run the agent again when more washers have been inspected.",
        },
    },
    "hi": {
        "vib": {
            "label": "मोटर कंपन",
            "state": "मोटर का कंपन पीली सीमा से ऊपर था",
            "title": "मोटर हिलने पर रिजेक्ट बढ़ते हैं",
            "fault": "ढीला मोटर माउंट या डगमगाती बेल्ट",
            "cause": "बेल्ट मोटर का माउंट ढीला हो गया है (या बेल्ट रोलर पर डगमगा रही है), इसलिए मोटर कंपन करके बेल्ट "
                     "और उस पर रखे वॉशर को हिलाती है।",
            "why": [
                "ज़्यादा वॉशर रिजेक्ट क्यों हुए? ज़्यादातर अतिरिक्त रिजेक्ट तब हुए जब मोटर हिल रही थी।",
                "कंपन से रिजेक्ट क्यों होते हैं? हिलती बेल्ट वॉशर को कैमरे के नीचे तिरछा और इधर-उधर कर देती है और गाइड "
                "से टकराती है, इसलिए तस्वीर धुंधली आती है और खरोंच दिखती हैं।",
                "मोटर क्यों हिल रही है? उसका माउंट ढीला हो गया है, या बेल्ट रोलर पर डगमगा रही है।",
                "माउंट ढीला क्यों हुआ? लगातार कंपन से बिना थ्रेड-लॉकर या स्प्रिंग वॉशर वाले पेंच धीरे-धीरे खुल जाते हैं।",
                "पहले क्यों नहीं पकड़ा गया? माउंट की नियमित जाँच नहीं होती और पीले कंपन अलार्म पर कार्रवाई नहीं हुई।",
            ],
            "contain": "हर वॉशर कैमरे से गुज़रता रहे और होल्ड वाले वॉशर हाथ से जाँचें। अगर कंपन पीला ही रहे, तो बेल्ट "
                       "रोकें और और वॉशर चलाने से पहले मोटर माउंट जाँचें।",
            "act": "बेल्ट रोकें, मोटर माउंट के पेंच कसें और थ्रेड-लॉकर या स्प्रिंग वॉशर लगाएँ। देखें कि बेल्ट सीधी चले और "
                   "रोलर पर बराबर कसी हो। फिर चालू करें और देखें कि कंपन पीली सीमा से नीचे आ जाए।",
            "prevent": "पीले कंपन को रुककर जाँचने का संकेत मानें। मोटर माउंट के पेंच और बेल्ट की सीध को शिफ्ट की "
                       "शुरुआत की चेकलिस्ट में जोड़ें। किसी भी मरम्मत के बाद सामान्य कंपन स्तर दोबारा सीखें।",
        },
        "lux": {
            "label": "कम रोशनी",
            "state": "टनल की रोशनी पीली सीमा से कम थी",
            "title": "टनल की रोशनी कम होने पर रिजेक्ट बढ़ते हैं",
            "fault": "धीमी या खराब टनल LED, या गंदा डिफ्यूज़र",
            "cause": "कैमरा टनल में रोशनी कम हो जाती है (धीमी या टिमटिमाती LED पट्टी, ढीला कनेक्टर या गंदा डिफ्यूज़र), "
                     "इसलिए तस्वीर अंधेरी आती है और अच्छे वॉशर भी AI के सीखे हुए अच्छे वॉशर जैसे नहीं दिखते।",
            "why": [
                "ज़्यादा वॉशर रिजेक्ट क्यों हुए? ज़्यादातर अतिरिक्त रिजेक्ट तब हुए जब टनल की रोशनी कम थी।",
                "कम रोशनी से रिजेक्ट क्यों होते हैं? अंधेरी तस्वीर में अच्छा वॉशर भी AI के सीखे हुए अच्छे वॉशर से अलग "
                "दिखता है, इसलिए उसे असामान्य माना जाता है।",
                "रोशनी कम क्यों है? टनल की LED पट्टी धीमी हो रही है या टिमटिमा रही है, या डिफ्यूज़र गंदा है।",
                "LED धीमी क्यों होती है? ढीला कनेक्टर, गिरती सप्लाई वोल्टेज या डिफ्यूज़र पर धूल रोशनी कम कर देती है।",
                "पहले क्यों नहीं पकड़ा गया? शिफ्ट की शुरुआत में टनल की रोशनी नहीं जाँची जाती और पीले रोशनी अलार्म पर "
                "कार्रवाई नहीं हुई।",
            ],
            "contain": "होल्ड वाले वॉशर हाथ से जाँचें। अगर रोशनी पीली ही रहे, तो जाँच रोकें और और वॉशर चलाने से पहले "
                       "रोशनी ठीक करें, क्योंकि AI अंधेरे में सही फैसला नहीं कर सकता।",
            "act": "डिफ्यूज़र और कैमरे का लेंस साफ़ करें। LED पट्टी का कनेक्टर और उसकी सप्लाई वोल्टेज जाँचें। अगर पट्टी "
                   "धीमी ही रहे तो बदलें। कैमरे का एक्सपोज़र लॉक रखें ताकि तस्वीर न बदले।",
            "prevent": "टनल की रोशनी की रीडिंग और लेंस की सफ़ाई को शिफ्ट की शुरुआत की चेकलिस्ट में जोड़ें। पीली रोशनी "
                       "को रुककर जाँचने का संकेत मानें। लाइन पर एक अतिरिक्त LED पट्टी रखें।",
        },
        "temp": {
            "label": "गरम मोटर",
            "state": "मोटर का तापमान पीली सीमा से ऊपर था",
            "title": "मोटर गरम होने पर रिजेक्ट बढ़ते हैं",
            "fault": "ओवरलोड मोटर",
            "cause": "बेल्ट मोटर पर ज़्यादा भार है और वह गरम चलती है, इसलिए बेल्ट की रफ़्तार कभी गिरती है कभी उछलती "
                     "है और वॉशर कैमरे के नीचे गलत जगह पहुँचते हैं।",
            "why": [
                "ज़्यादा वॉशर रिजेक्ट क्यों हुए? ज़्यादातर अतिरिक्त रिजेक्ट तब हुए जब मोटर गरम थी।",
                "गरम मोटर से रिजेक्ट क्यों होते हैं? ओवरलोड मोटर धीमी पड़ती है और झटके देती है, इसलिए वॉशर फिसलते हैं "
                "और कैमरे के नीचे बीच में नहीं रुकते।",
                "मोटर गरम क्यों है? उस पर ज़्यादा भार है: बेल्ट बहुत कसी है, कोई रोलर अटकता है या काम बहुत भारी है।",
                "यह अतिरिक्त भार किसी ने क्यों नहीं देखा? मोटर का करंट और तापमान साथ में नहीं देखे गए।",
                "पहले क्यों नहीं पकड़ा गया? बेल्ट का कसाव, रोलर का खुलकर घूमना और मोटर की ठंडक नियमित चेकलिस्ट में "
                "नहीं हैं।",
            ],
            "contain": "होल्ड वाले वॉशर हाथ से जाँचें। अगर तापमान पीला ही रहे, तो बेल्ट रोकें और और वॉशर चलाने से पहले "
                       "मोटर को ठंडा होने दें।",
            "act": "बेल्ट रोकें और मोटर ठंडी होने दें। अतिरिक्त भार ढूँढें: बहुत कसी बेल्ट, जाम रोलर बेयरिंग या कचरा। "
                   "उसे हटाएँ, बेल्ट का कसाव सही करें और देखें कि मोटर तक हवा पहुँचे।",
            "prevent": "पीले मोटर तापमान को रुककर जाँचने का संकेत मानें। हर शिफ्ट बेल्ट का कसाव और हर रोलर का खुलकर "
                       "घूमना जाँचें। मोटर के आसपास हवा का रास्ता खुला रखें।",
        },
        "ma": {
            "label": "मोटर पर ज़ोर",
            "state": "बेल्ट मोटर का करंट पीली सीमा से ऊपर था",
            "title": "बेल्ट मोटर पर ज़ोर पड़ने पर रिजेक्ट बढ़ते हैं",
            "fault": "बेल्ट में रगड़ या जाम",
            "cause": "बेल्ट रगड़ रही है या वॉशर कहीं अटक रहे हैं (घर्षण या जाम), इसलिए मोटर ज़्यादा करंट खींचती है और "
                     "वॉशर घिसटते हैं, खरोंच खाते हैं और कैमरे के नीचे गलत जगह पहुँचते हैं।",
            "why": [
                "ज़्यादा वॉशर रिजेक्ट क्यों हुए? ज़्यादातर अतिरिक्त रिजेक्ट तब हुए जब मोटर का करंट ज़्यादा था।",
                "ज़्यादा करंट के साथ रिजेक्ट क्यों होते हैं? जब बेल्ट घिसटती है तो वॉशर गाइड में अटकते हैं, खरोंच खाते "
                "हैं या कैमरे के नीचे बीच में नहीं रुकते।",
                "बेल्ट क्यों घिसटती है? वह फ्रेम या गाइड से रगड़ती है, या किसी रोलर में कचरा फँसा है।",
                "ऐसा क्यों होता है? शिफ्ट के दौरान बेल्ट की सीध खिसकती है और कचरा जमा होता है।",
                "पहले क्यों नहीं पकड़ा गया? बेल्ट की सीध और गाइड की दूरी नियमित नहीं जाँची जाती और पीले करंट अलार्म पर "
                "कार्रवाई नहीं हुई।",
            ],
            "contain": "होल्ड वाले वॉशर हाथ से जाँचें। अगर करंट पीला ही रहे, तो बेल्ट रोकें और और वॉशर चलाने से पहले "
                       "जाम साफ़ करें।",
            "act": "बेल्ट रोकें, कचरा हटाएँ और गाइड खाली करें। बेल्ट की सीध ठीक करें ताकि वह बिना रगड़े सीधी चले। देखें "
                   "कि हर रोलर खुलकर घूमे।",
            "prevent": "पीले मोटर करंट को रुककर जाँचने का संकेत मानें। हर शिफ्ट बेल्ट की सीध और गाइड की दूरी जाँचें। "
                       "लाइन को वॉशर के कचरे से साफ़ रखें।",
        },
        None: {
            "label": "मशीन में कोई कारण नहीं",
            "title": "मशीन में कोई कारण नहीं मिला: खराबी शायद वॉशर के साथ ही आ रही है",
            "fault": "आने वाले वॉशर",
            "cause": "कोई भी मशीन सेंसर रिजेक्ट की वजह नहीं बताता: मोटर हिले, गरम हो, उस पर ज़ोर पड़े या रोशनी कम हो, "
                     "रिजेक्ट की दर लगभग एक जैसी रहती है। खराबी शायद वॉशर में ही है (आने वाला माल या पिछली प्रक्रिया), "
                     "या किसी ऐसी चीज़ से है जिसे सेंसर नहीं नापते।",
            "why": [
                "वॉशर रिजेक्ट क्यों हुए? कैमरे को उन पर असली निशान या आकार की खराबी मिली।",
                "खराबी मशीन की हालत के साथ क्यों नहीं बदलती? हर नापी गई मशीन स्थिति में रिजेक्ट की दर लगभग एक जैसी "
                "रहती है।",
                "क्या लाइन वॉशर खराब कर रही है? शायद नहीं; वॉशर खराबी के साथ ही आ रहे हैं।",
                "खराबी कहाँ से आती है? शायद आने वाले बैच से या इस स्टेशन से पहले की प्रक्रिया से।",
                "पहले क्यों नहीं पकड़ा गया? लाइन पर आने से पहले वॉशर का सैंपल नहीं जाँचा जाता।",
            ],
            "contain": "मौजूदा बैच अलग रखें, होल्ड और रिजेक्ट वॉशर का सैंपल हाथ से जाँचें, और हर वॉशर कैमरे से गुज़रता "
                       "रहे।",
            "act": "मौजूदा बैच का हाथ से सैंपल जाँचें। NAZAR में रिजेक्ट वॉशर की तस्वीरों में एक जैसी खराबी देखें। सबूत "
                   "सप्लायर या पिछले स्टेशन को भेजें।",
            "prevent": "हर नए बैच का लाइन पर जाने से पहले सैंपल जाँचें। हर शिफ्ट NAZAR का खराबी ट्रेंड देखें। ज़्यादा "
                       "वॉशर जाँचे जाने के बाद एजेंट फिर चलाएँ।",
        },
    },
}


def text(lang, key):
    return TEXT["hi" if lang == "hi" else "en"][key]
