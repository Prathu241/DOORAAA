"""
make_training_config.py -- Generate training_parameters.yaml for any keyword.

KEYWORD-GENERIC. Run once per keyword before training.

Usage:
    python make_training_config.py --keyword DORA
    python make_training_config.py --keyword AGNI
    python make_training_config.py --keyword DORA --steps 15000 --output training_parameters_DORA.yaml

The generated YAML uses the WAV-file "clips" interface so you can train
directly from the split/*.wav files -- no pre-generating mmap spectrograms first.

YAML fields are derived from the actual microWakeWord source:
    microwakeword/model_train_eval.py  -- load_config()
    microwakeword/train.py             -- train()
    microwakeword/data.py              -- FeatureHandler / ClipsHandlerWrapperGenerator
    notebooks/basic_training_notebook.ipynb -- reference config

VERIFIED FIELDS (confirmed against source):
    train_dir, clip_duration_ms, window_step_ms, batch_size
    training_steps, learning_rates, positive_class_weight, negative_class_weight
    eval_step_interval, target_minimization, minimization_metric, maximization_metric
    time_mask_max_size, time_mask_count, freq_mask_max_size, freq_mask_count
    features[*]: type, features_dir, truth, sampling_weight, penalty_weight,
                 truncation_strategy, clips_settings, augmentation_settings,
                 spectrogram_generation_settings

NOTE ON NEGATIVE DATA:
    This config uses the local background_wav/ and unknown_wav/ directories
    which currently have ~12 min of audio total. This is sufficient for
    initial development training but NOT for robust false-accept testing.

    For robust training download the official microWakeWord negative datasets:
        https://huggingface.co/datasets/kahrendt/microwakeword
    Files: dinner_party.zip, speech.zip, no_speech.zip, dinner_party_eval.zip
    Unzip into: negative_datasets/
    Then uncomment the mmap negative entries at the bottom of the generated YAML.
"""

import argparse
import os
import sys
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))


def make_config(
    keyword: str,
    steps: int,
    output_path: str,
    use_official_negatives: bool,
) -> dict:
    kw = keyword.strip().upper()

    # Absolute paths to the split directories for this keyword
    train_pos_dir = os.path.join(ROOT, "dataset", "split", "train", kw)
    val_pos_dir   = os.path.join(ROOT, "dataset", "split", "val",   kw)
    test_pos_dir  = os.path.join(ROOT, "dataset", "split", "test",  kw)
    bg_dir        = os.path.join(ROOT, "dataset", "background_wav")
    unk_dir       = os.path.join(ROOT, "dataset", "unknown_wav")

    # Warn about missing directories
    for label, d in [
        (f"split/train/{kw}", train_pos_dir),
        (f"split/val/{kw}",   val_pos_dir),
        (f"split/test/{kw}",  test_pos_dir),
        ("background_wav",    bg_dir),
        ("unknown_wav",       unk_dir),
    ]:
        if not os.path.isdir(d):
            print(f"  [WARN] Directory not found: {d}")
            print(f"         Run prepare_dataset.py --keyword {kw} first.")

    config = {}

    # ---- Core training settings (consumed by load_config + train.py) ---------
    config["train_dir"]        = os.path.join(ROOT, "trained_models", kw)
    config["clip_duration_ms"] = 1500   # max keyword duration the model accepts
    config["window_step_ms"]   = 10     # spectrogram step; matches micro_speech

    config["training_steps"]         = [steps]
    config["learning_rates"]         = [0.001]
    config["batch_size"]             = 128
    config["positive_class_weight"]  = [1]
    config["negative_class_weight"]  = [20]   # heavily penalise false negatives
    config["eval_step_interval"]     = 500

    # ---- SpecAugment (applied during training batches) -----------------------
    # Start with modest values; increase if model overfits
    config["time_mask_max_size"] = [5]
    config["time_mask_count"]    = [2]
    config["freq_mask_max_size"] = [5]
    config["freq_mask_count"]    = [2]

    # ---- Best-weights selection ----------------------------------------------
    # Minimize nothing (set to null) then maximize average_viable_recall.
    # To also target FA/hr: set minimization_metric to "ambient_false_positives_per_hour"
    # and target_minimization to e.g. 2.0. Requires validation_ambient data.
    config["target_minimization"]  = 0.9
    config["minimization_metric"]  = None    # null in YAML
    config["maximization_metric"]  = "average_viable_recall"

    # ---- Feature sets --------------------------------------------------------
    # Each entry follows FeatureHandler's ClipsHandlerWrapperGenerator interface.
    # "clips" type: loads WAV files on-the-fly with augmentation.
    # See microwakeword/data.py FeatureHandler and microwakeword/audio/clips.py

    features = []

    # -- Positive: keyword clips (train split) --------------------------------
    features.append({
        "type":                "clips",
        "truth":               True,
        "sampling_weight":     2.0,
        "penalty_weight":      1.0,
        "truncation_strategy": "truncate_start",
        "clips_settings": {
            "input_directory":        train_pos_dir,
            "file_pattern":           "*.wav",
            "max_clip_duration_s":    None,     # accept all durations
            "remove_silence":         False,
            "random_split_seed":      None,     # no splitting inside clips
            "split_count":            0,
        },
        "augmentation_settings": {
            "augmentation_duration_s": 3.2,
            "augmentation_probabilities": {
                "SevenBandParametricEQ": 0.1,
                "TanhDistortion":        0.0,
                "PitchShift":            0.1,
                "BandStopFilter":        0.0,
                "AddColorNoise":         0.1,
                "AddBackgroundNoise":    0.75,
                "Gain":                  1.0,
                "GainTransition":        0.25,
                "RIR":                   0.0,   # set > 0 if you have impulse responses
            },
            "impulse_paths":         [],        # add MIT RIR path here for reverb
            "background_paths":      [bg_dir],  # mix in background noise
            "background_min_snr_db": -5,
            "background_max_snr_db": 10,
            "min_jitter_s":          0.1,
            "max_jitter_s":          0.5,
        },
        "spectrogram_generation_settings": {
            "slide_frames": 10,   # simulate streaming; same spectrogram offset 10 times
            "step_ms":      10,
        },
    })

    # -- Negative: background / noise -----------------------------------------
    features.append({
        "type":                "clips",
        "truth":               False,
        "sampling_weight":     5.0,
        "penalty_weight":      1.0,
        "truncation_strategy": "random",
        "clips_settings": {
            "input_directory": bg_dir,
            "file_pattern":    "*.wav",
            "max_clip_duration_s": None,
            "remove_silence":  False,
            "random_split_seed": None,
            "split_count":     0,
        },
        "augmentation_settings": {
            "augmentation_duration_s": 3.2,
            "augmentation_probabilities": {
                "AddColorNoise":      0.25,
                "AddBackgroundNoise": 0.0,
                "Gain":               1.0,
                "GainTransition":     0.25,
            },
            "impulse_paths":  [],
            "background_paths": [],
            "background_min_snr_db": -10,
            "background_max_snr_db": 10,
            "min_jitter_s": 0.0,
            "max_jitter_s": 0.0,
        },
        "spectrogram_generation_settings": {
            "slide_frames": None,
            "step_ms":      10,
        },
    })

    # -- Negative: unknown speech + hard negatives ----------------------------
    features.append({
        "type":                "clips",
        "truth":               False,
        "sampling_weight":     10.0,
        "penalty_weight":      1.0,
        "truncation_strategy": "random",
        "clips_settings": {
            "input_directory": unk_dir,
            "file_pattern":    "*.wav",
            "max_clip_duration_s": None,
            "remove_silence":  False,
            "random_split_seed": None,
            "split_count":     0,
        },
        "augmentation_settings": {
            "augmentation_duration_s": 3.2,
            "augmentation_probabilities": {
                "AddColorNoise":      0.1,
                "AddBackgroundNoise": 0.5,
                "Gain":               1.0,
                "GainTransition":     0.25,
            },
            "impulse_paths":  [],
            "background_paths": [bg_dir],
            "background_min_snr_db": -5,
            "background_max_snr_db": 10,
            "min_jitter_s": 0.0,
            "max_jitter_s": 0.0,
        },
        "spectrogram_generation_settings": {
            "slide_frames": None,
            "step_ms":      10,
        },
    })

    # -- Official microWakeWord mmap negatives (commented-out placeholder) ----
    # Uncomment after downloading from HuggingFace:
    #   https://huggingface.co/datasets/kahrendt/microwakeword
    # MMAP entries use type:"mmap" which reads pre-generated RaggedMmap stores.
    # These provide hundreds of hours of speech/noise; critical for robust FA testing.
    if use_official_negatives:
        neg_base = os.path.join(ROOT, "negative_datasets")
        for neg_name, sweight, strategy in [
            ("speech",            10.0, "random"),
            ("dinner_party",      10.0, "random"),
            ("no_speech",          5.0, "random"),
            ("dinner_party_eval",  0.0, "split"),   # val/test only (sampling_weight=0)
        ]:
            neg_dir = os.path.join(neg_base, neg_name)
            if os.path.isdir(neg_dir):
                features.append({
                    "type":                "mmap",
                    "features_dir":        neg_dir,
                    "truth":               False,
                    "sampling_weight":     sweight,
                    "penalty_weight":      1.0,
                    "truncation_strategy": strategy,
                })
            else:
                print(f"  [WARN] Official negative not found: {neg_dir}")

    config["features"] = features

    return config


def main():
    parser = argparse.ArgumentParser(
        description="Generate microWakeWord training_parameters.yaml for a keyword."
    )
    parser.add_argument(
        "--keyword", required=True,
        help="Target keyword (e.g. DORA, AGNI).",
    )
    parser.add_argument(
        "--steps", default=15000, type=int,
        help="Number of training steps. Default 15000 (dev). "
             "Increase to 30000-50000 for final training.",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output YAML path. Default: training_parameters_<KEYWORD>.yaml",
    )
    parser.add_argument(
        "--use_official_negatives", action="store_true",
        help="Include mmap entries for official microWakeWord negative datasets "
             "(requires prior download from HuggingFace).",
    )
    args = parser.parse_args()

    kw          = args.keyword.strip().upper()
    output_path = args.output or os.path.join(ROOT, f"training_parameters_{kw}.yaml")

    print(f"\nGenerating training config for keyword: {kw}")
    print(f"Training steps : {args.steps}")
    print(f"Output         : {output_path}")
    if args.use_official_negatives:
        print(f"Negatives      : local + official mmap datasets")
    else:
        print(f"Negatives      : local only (background_wav + unknown_wav)")
        print(f"                 [WARN] Only ~12 min -- insufficient for FA testing.")
        print(f"                 Add --use_official_negatives after downloading HuggingFace data.")
    print()

    config = make_config(kw, args.steps, output_path, args.use_official_negatives)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"Written: {output_path}")

    # ---- Print the exact training command ------------------------------------
    print()
    print("=" * 64)
    print("EXACT TRAINING COMMAND (dry-run validated against --help):")
    print("=" * 64)
    print()
    print(f"  cd {os.path.join(ROOT, 'microWakeWord')}")
    print()
    print(f"  python -m microwakeword.model_train_eval \\")
    print(f"      --training_config \"{output_path}\" \\")
    print(f"      --train 1 \\")
    print(f"      --restore_checkpoint 1 \\")
    print(f"      --test_tf_nonstreaming 0 \\")
    print(f"      --test_tflite_nonstreaming 0 \\")
    print(f"      --test_tflite_nonstreaming_quantized 0 \\")
    print(f"      --test_tflite_streaming 0 \\")
    print(f"      --test_tflite_streaming_quantized 1 \\")
    print(f"      --use_weights best_weights \\")
    print(f"      mixednet \\")
    print(f"      --pointwise_filters \"64,64,64,64\" \\")
    print(f"      --repeat_in_block \"1,1,1,1\" \\")
    print(f"      --mixconv_kernel_sizes \"[5],[7,11],[9,15],[23]\" \\")
    print(f"      --residual_connection \"0,0,0,0\" \\")
    print(f"      --first_conv_filters 32 \\")
    print(f"      --first_conv_kernel_size 5 \\")
    print(f"      --stride 3")
    print()
    print(f"Output TFLite (quantized streaming) will be at:")
    train_dir = os.path.join(ROOT, "trained_models", kw)
    print(f"  {train_dir}")
    print(f"  └── tflite_stream_state_internal_quant/")
    print(f"      └── stream_state_internal_quant.tflite")
    print()
    print("NOTE: Do NOT start training until audit_dataset.py passes with 0 failures.")
    print("      Current blocker: download official negative datasets (12 min audio is not enough).")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    main()
