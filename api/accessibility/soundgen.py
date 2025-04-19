import base64
import io

import soundfile as sf
from tones import TRIANGLE_WAVE
from tones.mixer import Mixer


def delta_to_tone(deltas, alpha=1, sr=44100, duration=0.8, silence=0.2):
    mixer = Mixer(sr, 0.5)
    mixer.create_track(0, TRIANGLE_WAVE, attack=0.05, decay=0.1)

    def mag_to_tone(magnitude):
        if magnitude >= 0:
            min_frequency = 400
            max_frequency = 880
        else:
            min_frequency = 80
            max_frequency = 400
        if magnitude < 0:
            frequency = max_frequency - (max_frequency - min_frequency) * (abs(magnitude) / 100)
        else:
            frequency = min_frequency + (max_frequency - min_frequency) * (abs(magnitude) / 100)
        mixer.add_tone(0, frequency=frequency, duration=duration, attack=0.05, decay=0.1, amplitude=0.8)
        mixer.add_silence(0, silence)

    for d in deltas:
        mag_to_tone(alpha * d)
    samples = mixer.mix()
    buffer = io.BytesIO()
    sf.write(buffer, samples, sr, format='WAV')
    return base64.b64encode(buffer.getvalue()).decode('utf-8'), "audio/wav", duration + silence
