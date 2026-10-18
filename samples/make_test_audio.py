"""Generate a synthetic talking-head test video with varied speech content."""
import os
from gtts import gTTS

SAMPLES = os.path.dirname(os.path.abspath(__file__))

SCRIPT = [
    ("seg1.mp3", "Nobody talks about this, but I made twelve thousand dollars last month just by clipping other people's videos. Here is exactly how it works, step by step."),
    ("seg2.mp3", "Stop scrolling. If you have a phone and two hours a day, you can do this. You do not need followers. You do not need editing skills. You just need to post every single day."),
    ("seg3.mp3", "So I uploaded my first thirty clips, and honestly, most of them flopped. Three views. Eleven views. But then one clip hit two hundred thousand views overnight, and that one clip paid me more than my old job paid in a week."),
    ("seg4.mp3", "The weather today is partly cloudy with a slight chance of rain in the afternoon. Traffic on the highway is moving slowly due to construction near the downtown exit."),
    ("seg5.mp3", "Here is the mistake that kills ninety percent of beginners. They quit after two weeks. The algorithm needs time to learn who likes your clips. So the real secret is simple. Never miss a day for ninety days straight."),
    ("seg6.mp3", "What would you do with an extra five hundred dollars a month? For me, it meant I could finally quit the night shift. And the crazy part? I started with zero dollars and a three year old phone."),
]

os.makedirs(SAMPLES, exist_ok=True)
mp3s = []
for fname, text in SCRIPT:
    p = os.path.join(SAMPLES, fname)
    gTTS(text=text, lang="en").save(p)
    mp3s.append(p)
    print("saved", fname)

# concat audio
with open(os.path.join(SAMPLES, "list.txt"), "w") as f:
    for p in mp3s:
        f.write(f"file '{p}'\n")
print("AUDIO_DONE")
