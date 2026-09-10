#!/usr/bin/env bash
# =============================================================================
# swap_keyword.sh -- Full keyword pipeline for SIH / ISRO custom keyword.
#
# KEYWORD-GENERIC. Works for DORA (dev) and any ISRO-assigned keyword.
#
# Usage:
#   ./swap_keyword.sh DORA              # Run full pipeline
#   ./swap_keyword.sh AGNI              # Run full pipeline for new keyword
#   ./swap_keyword.sh DORA --validate   # Validate only, no generation/training
#   ./swap_keyword.sh DORA --dryrun     # Show what would run, do nothing
#
# Prerequisites:
#   - Python 3.10+ with microWakeWord installed:  pip install -e microWakeWord/
#   - piper-tts installed:                         pip install piper-tts
#   - ffmpeg on PATH:                              winget install Gyan.FFmpeg
#   - piper_voices/ downloaded:
#       python generate_keyword_dataset.py --download_voices
#   - dataset/Raw/<KEYWORD>/ OR dataset/<KEYWORD>_real/ with WAV recordings
#   - microWakeWord repository cloned in microWakeWord/
#   - Official microWakeWord negative datasets in negative_datasets/
#       (download from https://huggingface.co/datasets/kahrendt/microwakeword)
#
# Pipeline steps:
#   1.  Validate keyword argument
#   2.  Check prerequisites (Python, piper, ffmpeg, voices, negatives)
#   3.  Convert raw recordings to 16kHz mono PCM_16 WAV  (if not done)
#   4.  Generate Piper TTS synthetic samples              (if piper voices present)
#   5.  Generate hard negatives                           (if piper voices present)
#   6.  Augment real recordings  (4x variants, PCM_16)
#   7.  Build group-disjoint train/val/test split
#   8.  Run dataset quality audit (leakage + format check)
#   9.  Generate keyword-specific training_parameters_<KW>.yaml
#   10. Print the exact training command -- DO NOT auto-launch training
#
# STEP 10 intentionally does NOT auto-launch training.
# You must verify audit output is clean, then run the printed command manually.
# =============================================================================

set -euo pipefail

# ── Colours (optional -- degrade gracefully if terminal doesn't support them) -
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[0;33m'
BLU='\033[0;34m'; BOLD='\033[1m'; RESET='\033[0m'
# Disable colours if not a tty
if [ ! -t 1 ]; then RED=''; GRN=''; YLW=''; BLU=''; BOLD=''; RESET=''; fi

info()  { echo -e "${BLU}[INFO]${RESET}  $*"; }
ok()    { echo -e "${GRN}[ OK ]${RESET}  $*"; }
warn()  { echo -e "${YLW}[WARN]${RESET}  $*"; }
err()   { echo -e "${RED}[ERR ]${RESET}  $*" >&2; }
die()   { err "$*"; exit 1; }
sep()   { echo -e "${BOLD}$(printf '=%.0s' {1..64})${RESET}"; }
sep2()  { echo "$(printf -- '-%.0s' {1..64})"; }

# ── Parse arguments -----------------------------------------------------------
KEYWORD=""
DRYRUN=0
VALIDATE_ONLY=0
SKIP_SYNTH=0
SKIP_HARD_NEG=0
TRAINING_STEPS=15000

for arg in "$@"; do
    case "$arg" in
        --dryrun)         DRYRUN=1 ;;
        --validate)       VALIDATE_ONLY=1 ;;
        --skip-synth)     SKIP_SYNTH=1 ;;
        --skip-hardneg)   SKIP_HARD_NEG=1 ;;
        --steps=*)        TRAINING_STEPS="${arg#*=}" ;;
        --help|-h)
            sed -n '2,30p' "$0" | sed 's/^# //; s/^#//'
            exit 0 ;;
        -*)
            die "Unknown option: $arg  (run with --help)" ;;
        *)
            [ -z "$KEYWORD" ] && KEYWORD="$arg" || die "Unexpected argument: $arg" ;;
    esac
done

# ── Step 1: Validate keyword --------------------------------------------------
sep
echo -e "${BOLD}  DORA / SIH Keyword Pipeline${RESET}"
sep
echo ""

[ -z "$KEYWORD" ] && die "Keyword is required.\n  Usage: ./swap_keyword.sh KEYWORD [--validate] [--dryrun]"

KW="${KEYWORD^^}"   # uppercase
kw="${KEYWORD,,}"   # lowercase

info "Keyword        : $KW"
info "Mode           : $([ $DRYRUN -eq 1 ] && echo DRY-RUN || ([ $VALIDATE_ONLY -eq 1 ] && echo VALIDATE-ONLY || echo FULL))"
info "Training steps : $TRAINING_STEPS  (used only when generating YAML)"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run() {
    # Wrapper: print command, execute if not dryrun
    echo -e "${BLU}  \$${RESET} $*"
    if [ $DRYRUN -eq 0 ]; then
        eval "$@"
    fi
}

# ── Step 2: Check prerequisites -----------------------------------------------
sep2
info "Step 2: Checking prerequisites"
sep2
echo ""

PREREQ_OK=1

check_cmd() {
    if command -v "$1" &>/dev/null; then
        ok "$1 found"
    else
        err "$1 NOT found -- $2"
        PREREQ_OK=0
    fi
}

check_cmd python   "Install Python 3.10+"
check_cmd ffmpeg   "winget install Gyan.FFmpeg"
check_cmd piper    "pip install piper-tts"

# Check microWakeWord is importable
if python -c "import microwakeword" &>/dev/null 2>&1; then
    ok "microwakeword importable"
else
    err "microwakeword not importable -- cd microWakeWord && pip install -e ."
    PREREQ_OK=0
fi

# Check piper voices
VOICES_DIR="$SCRIPT_DIR/piper_voices"
N_VOICES=$(find "$VOICES_DIR" -name "*.onnx" 2>/dev/null | wc -l | tr -d ' ')
if [ "$N_VOICES" -gt 0 ]; then
    ok "Piper voices: $N_VOICES model(s) in piper_voices/"
    HAS_VOICES=1
else
    warn "No .onnx files in piper_voices/ -- TTS synthesis will be skipped."
    warn "Download with: python generate_keyword_dataset.py --download_voices"
    HAS_VOICES=0
fi

# Check official negatives
NEG_DIR="$SCRIPT_DIR/negative_datasets"
HAS_OFFICIAL_NEG=0
if [ -d "$NEG_DIR/speech" ] || [ -d "$NEG_DIR/dinner_party" ]; then
    ok "Official negative datasets found in negative_datasets/"
    HAS_OFFICIAL_NEG=1
else
    warn "Official negative datasets NOT found."
    warn "Download from: https://huggingface.co/datasets/kahrendt/microwakeword"
    warn "Files: dinner_party.zip, speech.zip, no_speech.zip, dinner_party_eval.zip"
    warn "Unzip into: negative_datasets/"
    warn "Training will proceed with local negatives only (~12 min) -- NOT recommended for final eval."
fi
echo ""

if [ $PREREQ_OK -eq 0 ]; then
    die "One or more prerequisites are missing. Fix them and re-run."
fi

[ $VALIDATE_ONLY -eq 1 ] && { info "Validate-only mode -- skipping data generation."; }

# ── Step 3: Convert raw recordings to WAV ------------------------------------
sep2
info "Step 3: Convert raw recordings to 16kHz mono PCM_16 WAV"
sep2
echo ""

RAW_SRC="$SCRIPT_DIR/dataset/Raw/${KW}"
REAL_DIR="$SCRIPT_DIR/dataset/${KW}_real"

if [ $VALIDATE_ONLY -eq 0 ]; then
    if [ -d "$RAW_SRC" ] && [ "$(find "$RAW_SRC" -name '*.aac' -o -name '*.mp3' -o -name '*.ogg' 2>/dev/null | wc -l)" -gt 0 ]; then
        info "Found raw audio in $RAW_SRC -- converting with convert_aac.py"
        run "python '$SCRIPT_DIR/convert_aac.py' 2>/dev/null || python '$SCRIPT_DIR/convert_negatives.py'"
        # Note: convert_aac.py is designed for DORA_real; for other keywords
        # use convert_negatives.py logic or run ffmpeg directly.
    elif [ -d "$REAL_DIR" ]; then
        N_REAL=$(find "$REAL_DIR" -name '*.wav' | wc -l | tr -d ' ')
        ok "Using existing $REAL_DIR ($N_REAL WAV files)"
    else
        warn "No raw recordings found for $KW in $RAW_SRC or $REAL_DIR"
        warn "Record them manually: python record_keyword.py --keyword $KW --speaker spk001 --count 20"
    fi
fi
echo ""

# ── Step 4: TTS synthesis -----------------------------------------------------
sep2
info "Step 4: Piper TTS synthesis (~600 synthetic samples)"
sep2
echo ""

SYNTH_DIR="$SCRIPT_DIR/dataset/${KW}_synthetic"

if [ $VALIDATE_ONLY -eq 0 ] && [ $SKIP_SYNTH -eq 0 ]; then
    if [ $HAS_VOICES -eq 1 ]; then
        N_EXISTING=$(find "$SYNTH_DIR" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')
        if [ "$N_EXISTING" -ge 500 ]; then
            ok "Synthetic samples already exist: $N_EXISTING in $SYNTH_DIR"
        else
            info "Generating Piper TTS samples for $KW..."
            run "python '$SCRIPT_DIR/generate_keyword_dataset.py' --keyword '$KW' --count 600"
        fi
    else
        warn "Skipping TTS synthesis -- no piper voice models."
    fi
else
    info "TTS synthesis skipped (--skip-synth or --validate mode)."
fi
echo ""

# ── Step 5: Hard negatives ----------------------------------------------------
sep2
info "Step 5: Generate phonetically-confusable hard negatives"
sep2
echo ""

HN_DIR="$SCRIPT_DIR/dataset/${KW}_hard_negatives"

if [ $VALIDATE_ONLY -eq 0 ] && [ $SKIP_HARD_NEG -eq 0 ]; then
    if [ $HAS_VOICES -eq 1 ]; then
        N_HN=$(find "$HN_DIR" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')
        if [ "$N_HN" -ge 100 ]; then
            ok "Hard negatives already exist: $N_HN in $HN_DIR"
        else
            info "Generating hard negatives for $KW..."
            run "python '$SCRIPT_DIR/generate_hard_negatives.py' --keyword '$KW' --count 150"
            if [ -d "$HN_DIR" ]; then
                info "Copying hard negatives into unknown_wav/..."
                run "cp '$HN_DIR'/*.wav '$SCRIPT_DIR/dataset/unknown_wav/'"
            fi
        fi
    else
        warn "Skipping hard negatives -- no piper voice models."
    fi
else
    info "Hard negatives skipped."
fi
echo ""

# ── Step 6: Augmentation ------------------------------------------------------
sep2
info "Step 6: Augment real recordings (4x: noise, pitch, speed, reverb) -- PCM_16"
sep2
echo ""

AUG_DIR="$SCRIPT_DIR/dataset/${KW}_augmented"

if [ $VALIDATE_ONLY -eq 0 ]; then
    # Check source recordings exist
    N_REAL_WAV=$(find "$REAL_DIR" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$N_REAL_WAV" -gt 0 ]; then
        N_AUG=$(find "$AUG_DIR" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')
        EXPECTED_AUG=$((N_REAL_WAV * 4))
        if [ "$N_AUG" -eq "$EXPECTED_AUG" ]; then
            ok "Augmented files already correct: $N_AUG (= $N_REAL_WAV x 4)"
        else
            info "Running augmentation ($N_REAL_WAV source files -> $EXPECTED_AUG augmented)..."
            # Remove stale augmented dir if count is wrong
            [ "$N_AUG" -gt 0 ] && run "rm -rf '$AUG_DIR'"
            run "python '$SCRIPT_DIR/augment_real.py' --keyword '$KW' --input '$REAL_DIR' --output '$AUG_DIR'"
        fi
    else
        warn "No real WAV recordings found in $REAL_DIR -- skipping augmentation."
        warn "Record manually or run TTS synthesis first."
    fi
fi
echo ""

# ── Step 7: Group-disjoint split ----------------------------------------------
sep2
info "Step 7: Build base-recording-disjoint train/val/test split"
sep2
echo ""

SPLIT_TRAIN="$SCRIPT_DIR/dataset/split/train/$KW"
SPLIT_VAL="$SCRIPT_DIR/dataset/split/val/$KW"
SPLIT_TEST="$SCRIPT_DIR/dataset/split/test/$KW"

if [ $VALIDATE_ONLY -eq 0 ]; then
    # Always rebuild split to reflect current data state
    info "Rebuilding split (removes old split/$KW dirs)..."
    run "rm -rf '$SPLIT_TRAIN' '$SPLIT_VAL' '$SPLIT_TEST'"
    run "python '$SCRIPT_DIR/prepare_dataset.py' --keyword '$KW'"
fi
echo ""

# ── Step 8: Dataset quality audit --------------------------------------------
sep2
info "Step 8: Running dataset quality audit"
sep2
echo ""

run "python '$SCRIPT_DIR/audit_dataset.py' --keyword '$KW'"
AUDIT_EXIT=$?

if [ $DRYRUN -eq 0 ] && [ $AUDIT_EXIT -ne 0 ]; then
    echo ""
    warn "Audit reported failures. Review output above."
    warn "If failures are only the negative-data warnings, you may proceed"
    warn "to training for development, but expect elevated false-accept rate."
    warn "For SIH final evaluation, fix all failures before training."
    echo ""
    # Do not hard-exit: allow YAML generation and command print to proceed
fi
echo ""

# ── Step 9: Generate training YAML -------------------------------------------
sep2
info "Step 9: Generating training configuration YAML"
sep2
echo ""

YAML_PATH="$SCRIPT_DIR/training_parameters_${KW}.yaml"
OFFICIAL_FLAG=""
[ $HAS_OFFICIAL_NEG -eq 1 ] && OFFICIAL_FLAG="--use_official_negatives"

run "python '$SCRIPT_DIR/make_training_config.py' --keyword '$KW' --steps $TRAINING_STEPS $OFFICIAL_FLAG --output '$YAML_PATH'"
echo ""

# ── Step 10: Print training command (DO NOT auto-launch) ---------------------
sep
echo -e "${BOLD}  Step 10: Training command (NOT auto-launched)${RESET}"
sep
echo ""
echo -e "${YLW}  Training is NOT started automatically.${RESET}"
echo -e "${YLW}  Review the audit output above, then run the command below manually.${RESET}"
echo ""
echo -e "${BOLD}  cd '$SCRIPT_DIR/microWakeWord'${RESET}"
echo ""
echo -e "${BOLD}  python -m microwakeword.model_train_eval \\${RESET}"
echo -e "${BOLD}      --training_config '$YAML_PATH' \\${RESET}"
echo -e "${BOLD}      --train 1 \\${RESET}"
echo -e "${BOLD}      --restore_checkpoint 1 \\${RESET}"
echo -e "${BOLD}      --test_tf_nonstreaming 0 \\${RESET}"
echo -e "${BOLD}      --test_tflite_nonstreaming 0 \\${RESET}"
echo -e "${BOLD}      --test_tflite_nonstreaming_quantized 0 \\${RESET}"
echo -e "${BOLD}      --test_tflite_streaming 0 \\${RESET}"
echo -e "${BOLD}      --test_tflite_streaming_quantized 1 \\${RESET}"
echo -e "${BOLD}      --use_weights best_weights \\${RESET}"
echo -e "${BOLD}      mixednet \\${RESET}"
echo -e "${BOLD}      --pointwise_filters \"64,64,64,64\" \\${RESET}"
echo -e "${BOLD}      --repeat_in_block \"1,1,1,1\" \\${RESET}"
echo -e "${BOLD}      --mixconv_kernel_sizes \"[5],[7,11],[9,15],[23]\" \\${RESET}"
echo -e "${BOLD}      --residual_connection \"0,0,0,0\" \\${RESET}"
echo -e "${BOLD}      --first_conv_filters 32 \\${RESET}"
echo -e "${BOLD}      --first_conv_kernel_size 5 \\${RESET}"
echo -e "${BOLD}      --stride 3${RESET}"
echo ""
echo -e "  Output TFLite (quantized streaming):"
echo -e "    ${SCRIPT_DIR}/trained_models/${KW}/tflite_stream_state_internal_quant/"
echo -e "    └── stream_state_internal_quant.tflite"
echo ""

# ── Final summary -------------------------------------------------------------
sep
echo -e "${BOLD}  PIPELINE COMPLETE -- keyword: $KW${RESET}"
sep
echo ""

N_TRAIN=$(find "$SPLIT_TRAIN" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')
N_VAL=$(find "$SPLIT_VAL"   -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')
N_TEST=$(find "$SPLIT_TEST"  -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')
N_BG=$(find "$SCRIPT_DIR/dataset/background_wav" -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')
N_UNK=$(find "$SCRIPT_DIR/dataset/unknown_wav"   -name '*.wav' 2>/dev/null | wc -l | tr -d ' ')

echo "  Dataset summary:"
echo "    Keyword          : $KW"
echo "    Train positives  : $N_TRAIN"
echo "    Val   positives  : $N_VAL"
echo "    Test  positives  : $N_TEST"
echo "    Background neg   : $N_BG"
echo "    Unknown/HN neg   : $N_UNK"
echo "    Training YAML    : $YAML_PATH"
echo ""

if [ $AUDIT_EXIT -ne 0 ]; then
    warn "Audit had failures -- see output above before training."
else
    ok "Audit passed -- dataset is ready."
fi

echo ""
echo "  Next steps:"
echo "    1. Review audit output above."
[ $HAS_OFFICIAL_NEG -eq 0 ] && echo "    2. [BLOCKER] Download official negatives for robust FA testing."
echo "    3. Run the training command printed in Step 10."
echo "    4. After training: python audit_dataset.py --keyword $KW"
echo "    5. Measure on ESP32-S3: RAM, CPU, latency -- do not claim metrics until measured."
echo ""
