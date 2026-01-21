"""Procedural sound generator for 8-bit style effects."""

import math
import os
import struct
import wave
from typing import List


def generate_sine_wave(frequency: float, duration: float, sample_rate: int = 44100,
                       volume: float = 0.5) -> List[int]:
    """Generate a sine wave."""
    samples = []
    num_samples = int(duration * sample_rate)
    for i in range(num_samples):
        t = i / sample_rate
        value = math.sin(2 * math.pi * frequency * t)
        samples.append(int(value * volume * 32767))
    return samples


def generate_square_wave(frequency: float, duration: float, sample_rate: int = 44100,
                         volume: float = 0.3) -> List[int]:
    """Generate a square wave (8-bit sound)."""
    samples = []
    num_samples = int(duration * sample_rate)
    period = sample_rate / frequency
    for i in range(num_samples):
        if (i % period) < (period / 2):
            samples.append(int(volume * 32767))
        else:
            samples.append(int(-volume * 32767))
    return samples


def generate_noise(duration: float, sample_rate: int = 44100,
                   volume: float = 0.3) -> List[int]:
    """Generate white noise."""
    import random
    samples = []
    num_samples = int(duration * sample_rate)
    for _ in range(num_samples):
        samples.append(int((random.random() * 2 - 1) * volume * 32767))
    return samples


def apply_envelope(samples: List[int], attack: float = 0.01, decay: float = 0.1,
                   sustain: float = 0.7, release: float = 0.1,
                   sample_rate: int = 44100) -> List[int]:
    """Apply ADSR envelope to samples."""
    result = []
    num_samples = len(samples)
    attack_samples = int(attack * sample_rate)
    decay_samples = int(decay * sample_rate)
    release_samples = int(release * sample_rate)
    sustain_samples = num_samples - attack_samples - decay_samples - release_samples

    for i, sample in enumerate(samples):
        if i < attack_samples:
            # Attack phase
            env = i / attack_samples if attack_samples > 0 else 1.0
        elif i < attack_samples + decay_samples:
            # Decay phase
            progress = (i - attack_samples) / decay_samples if decay_samples > 0 else 1.0
            env = 1.0 - (1.0 - sustain) * progress
        elif i < attack_samples + decay_samples + sustain_samples:
            # Sustain phase
            env = sustain
        else:
            # Release phase
            progress = (i - attack_samples - decay_samples - sustain_samples) / release_samples
            env = sustain * (1.0 - progress) if release_samples > 0 else 0
        result.append(int(sample * env))
    return result


def save_wav(samples: List[int], filepath: str, sample_rate: int = 44100) -> None:
    """Save samples as a WAV file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with wave.open(filepath, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for sample in samples:
            wav_file.writeframes(struct.pack('<h', max(-32768, min(32767, sample))))


def generate_card_deal_sound(filepath: str) -> None:
    """Generate a card deal whoosh sound."""
    sample_rate = 44100
    duration = 0.15

    # Mix of noise with frequency sweep
    samples = generate_noise(duration, sample_rate, 0.2)

    # Add a quick frequency sweep
    sweep_samples = []
    num_samples = int(duration * sample_rate)
    for i in range(num_samples):
        t = i / sample_rate
        freq = 800 - 600 * (t / duration)  # Sweep from 800 to 200 Hz
        value = math.sin(2 * math.pi * freq * t) * 0.15
        sweep_samples.append(int(value * 32767))

    # Mix
    for i in range(len(samples)):
        samples[i] = (samples[i] + sweep_samples[i]) // 2

    samples = apply_envelope(samples, attack=0.005, decay=0.05, sustain=0.3, release=0.08)
    save_wav(samples, filepath, sample_rate)


def generate_card_flip_sound(filepath: str) -> None:
    """Generate a card flip click sound."""
    sample_rate = 44100
    duration = 0.08

    # Short click with harmonics
    samples = []
    num_samples = int(duration * sample_rate)
    for i in range(num_samples):
        t = i / sample_rate
        # Multiple harmonics for a richer click
        value = (math.sin(2 * math.pi * 1200 * t) * 0.3 +
                 math.sin(2 * math.pi * 2400 * t) * 0.15 +
                 math.sin(2 * math.pi * 600 * t) * 0.2)
        samples.append(int(value * 32767))

    samples = apply_envelope(samples, attack=0.001, decay=0.03, sustain=0.2, release=0.04)
    save_wav(samples, filepath, sample_rate)


def generate_chip_sound(filepath: str) -> None:
    """Generate a chip clink sound."""
    sample_rate = 44100
    duration = 0.2

    samples = []
    num_samples = int(duration * sample_rate)
    for i in range(num_samples):
        t = i / sample_rate
        # High metallic frequencies
        value = (math.sin(2 * math.pi * 3000 * t) * 0.2 +
                 math.sin(2 * math.pi * 4500 * t) * 0.15 +
                 math.sin(2 * math.pi * 6000 * t) * 0.1)
        samples.append(int(value * 32767))

    samples = apply_envelope(samples, attack=0.001, decay=0.05, sustain=0.1, release=0.14)
    save_wav(samples, filepath, sample_rate)


def generate_win_sound(filepath: str) -> None:
    """Generate a win jingle (ascending notes)."""
    sample_rate = 44100
    notes = [523, 659, 784, 1047]  # C5, E5, G5, C6
    note_duration = 0.1
    gap = 0.02

    all_samples = []
    for note in notes:
        samples = generate_square_wave(note, note_duration, sample_rate, 0.25)
        samples = apply_envelope(samples, attack=0.005, decay=0.02, sustain=0.6, release=0.05)
        all_samples.extend(samples)
        all_samples.extend([0] * int(gap * sample_rate))

    save_wav(all_samples, filepath, sample_rate)


def generate_lose_sound(filepath: str) -> None:
    """Generate a lose sound (descending notes)."""
    sample_rate = 44100
    notes = [392, 349, 311, 262]  # G4, F4, Eb4, C4
    note_duration = 0.12
    gap = 0.02

    all_samples = []
    for note in notes:
        samples = generate_square_wave(note, note_duration, sample_rate, 0.2)
        samples = apply_envelope(samples, attack=0.005, decay=0.03, sustain=0.5, release=0.06)
        all_samples.extend(samples)
        all_samples.extend([0] * int(gap * sample_rate))

    save_wav(all_samples, filepath, sample_rate)


def generate_blackjack_sound(filepath: str) -> None:
    """Generate a blackjack fanfare."""
    sample_rate = 44100
    # Arpeggio chord
    notes = [523, 659, 784, 1047, 1319]  # C major arpeggio up to E6
    note_duration = 0.08
    gap = 0.01

    all_samples = []
    for i, note in enumerate(notes):
        vol = 0.3 - i * 0.03
        samples = generate_square_wave(note, note_duration, sample_rate, vol)
        samples = apply_envelope(samples, attack=0.002, decay=0.02, sustain=0.6, release=0.04)
        all_samples.extend(samples)
        all_samples.extend([0] * int(gap * sample_rate))

    # Final sustained chord
    chord_duration = 0.3
    chord_samples = []
    num_samples = int(chord_duration * sample_rate)
    for i in range(num_samples):
        t = i / sample_rate
        value = (math.sin(2 * math.pi * 1047 * t) * 0.2 +
                 math.sin(2 * math.pi * 1319 * t) * 0.15 +
                 math.sin(2 * math.pi * 1568 * t) * 0.1)
        chord_samples.append(int(value * 32767))
    chord_samples = apply_envelope(chord_samples, attack=0.01, decay=0.1, sustain=0.4, release=0.15)
    all_samples.extend(chord_samples)

    save_wav(all_samples, filepath, sample_rate)


def generate_bust_sound(filepath: str) -> None:
    """Generate a bust thud sound."""
    sample_rate = 44100
    duration = 0.25

    # Low thud with noise
    samples = []
    num_samples = int(duration * sample_rate)
    for i in range(num_samples):
        t = i / sample_rate
        freq = 150 - 100 * (t / duration)  # Descending low frequency
        value = math.sin(2 * math.pi * freq * t) * 0.4
        samples.append(int(value * 32767))

    # Add some noise
    noise = generate_noise(duration, sample_rate, 0.15)
    for i in range(len(samples)):
        samples[i] = (samples[i] + noise[i]) // 2

    samples = apply_envelope(samples, attack=0.005, decay=0.08, sustain=0.2, release=0.15)
    save_wav(samples, filepath, sample_rate)


def generate_button_click_sound(filepath: str) -> None:
    """Generate a UI button click."""
    sample_rate = 44100
    duration = 0.05

    samples = generate_square_wave(800, duration, sample_rate, 0.2)
    samples = apply_envelope(samples, attack=0.001, decay=0.015, sustain=0.3, release=0.03)
    save_wav(samples, filepath, sample_rate)


def generate_button_hover_sound(filepath: str) -> None:
    """Generate a subtle hover sound."""
    sample_rate = 44100
    duration = 0.03

    samples = generate_sine_wave(1200, duration, sample_rate, 0.1)
    samples = apply_envelope(samples, attack=0.002, decay=0.01, sustain=0.2, release=0.015)
    save_wav(samples, filepath, sample_rate)


def generate_shuffle_sound(filepath: str) -> None:
    """Generate a card shuffle sound."""
    sample_rate = 44100
    duration = 0.5

    # Multiple card riffle sounds
    samples = [0] * int(duration * sample_rate)

    import random
    random.seed(42)  # Reproducible

    num_riffles = 15
    for _ in range(num_riffles):
        start = random.randint(0, int(duration * sample_rate * 0.8))
        riffle_duration = 0.03 + random.random() * 0.02

        riffle = generate_noise(riffle_duration, sample_rate, 0.15)
        riffle = apply_envelope(riffle, attack=0.002, decay=0.01, sustain=0.3, release=0.015)

        for i, s in enumerate(riffle):
            if start + i < len(samples):
                samples[start + i] = max(-32767, min(32767, samples[start + i] + s))

    save_wav(samples, filepath, sample_rate)


def generate_all_sounds(output_dir: str) -> None:
    """Generate all game sounds."""
    os.makedirs(output_dir, exist_ok=True)

    print("Generating sounds...")
    generate_card_deal_sound(os.path.join(output_dir, "card_deal.wav"))
    print("  - card_deal.wav")

    generate_card_flip_sound(os.path.join(output_dir, "card_flip.wav"))
    print("  - card_flip.wav")

    generate_chip_sound(os.path.join(output_dir, "chip_stack.wav"))
    print("  - chip_stack.wav")

    generate_chip_sound(os.path.join(output_dir, "chip_single.wav"))
    print("  - chip_single.wav")

    generate_win_sound(os.path.join(output_dir, "win.wav"))
    print("  - win.wav")

    generate_lose_sound(os.path.join(output_dir, "lose.wav"))
    print("  - lose.wav")

    generate_blackjack_sound(os.path.join(output_dir, "blackjack.wav"))
    print("  - blackjack.wav")

    generate_bust_sound(os.path.join(output_dir, "bust.wav"))
    print("  - bust.wav")

    generate_button_click_sound(os.path.join(output_dir, "button_click.wav"))
    print("  - button_click.wav")

    generate_button_hover_sound(os.path.join(output_dir, "button_hover.wav"))
    print("  - button_hover.wav")

    generate_shuffle_sound(os.path.join(output_dir, "shuffle.wav"))
    print("  - shuffle.wav")

    print("Done!")


if __name__ == "__main__":
    # Generate sounds when run directly
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base, "assets", "sounds")
    generate_all_sounds(output_dir)
