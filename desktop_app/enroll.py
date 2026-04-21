from audio.voice_auth import enroll_voice


def main() -> None:
    """
    Run the manual voice enrollment helper.

    Keeping the interactive flow behind `main()` avoids import-time prompts
    after the desktop package split.
    """
    print("Place 5-10 .wav recordings of your voice in Audio/samples/")
    print("Say different things in each sample, at least 5 seconds each")
    input("Press Enter when ready...")
    enroll_voice()


if __name__ == "__main__":
    main()
