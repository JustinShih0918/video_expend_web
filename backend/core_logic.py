import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torchvision import transforms
from tqdm import tqdm
import os
import sys
import subprocess
import shutil
from pathlib import Path

# Import the model and utilities
from models.generator import UNetGenerator
from utils.mask_utils import m11_to_01


# ==== Helper functions from test_video.py ====
def snap_up(x: int, mult: int) -> int:
    """Round up x to the nearest multiple of mult"""
    return (x + mult - 1) // mult * mult


def build_center_canvas_and_mask(img_S, S, Hc, Wc, device):
    """
    Place the SxS image in the center of HcxWc canvas and create mask.
    Mask: 0 = keep original, 1 = inpaint
    """
    top = (Hc - S) // 2
    left = (Wc - S) // 2
    bot = top + S
    right = left + S
    canvas = torch.zeros(1, 3, Hc, Wc, device=device)
    canvas[:, :, top:bot, left:right] = img_S
    mask = torch.ones(1, 1, Hc, Wc, device=device)
    mask[:, :, top:bot, left:right] = 0
    return canvas, mask


def forward_with_auto_snap(G, canvas, mask, multiples=(64, 128, 256, 512), pad_mode_canvas="reflect"):
    """
    Try different padding multiples to avoid size mismatch errors.
    """
    _, _, Hc, Wc = canvas.shape
    for mult in multiples:
        Hs = snap_up(Hc, mult)
        Ws = snap_up(Wc, mult)
        pad_r, pad_b = Ws - Wc, Hs - Hc
        try:
            if pad_mode_canvas in ("reflect", "replicate"):
                canvas_big = F.pad(canvas, (0, pad_r, 0, pad_b), mode=pad_mode_canvas)
            else:
                canvas_big = F.pad(canvas, (0, pad_r, 0, pad_b), mode="constant", value=0)
            mask_big = F.pad(mask, (0, pad_r, 0, pad_b), mode="constant", value=1)
            cond = torch.cat([canvas_big * (1 - mask_big), mask_big], dim=1)
            with torch.no_grad():
                pred_big_m11 = G(cond)
            pred_big = m11_to_01(pred_big_m11).clamp(0, 1)
            final_big = pred_big * mask_big + canvas_big * (1 - mask_big)
            return final_big[:, :, :Hc, :Wc]
        except RuntimeError as e:
            if "Sizes of tensors must match" in str(e):
                continue
            raise
    raise RuntimeError(f"All multiples failed for target {Hc}x{Wc}.")


class VideoExpander:
    def __init__(self, model_path, device=None, image_size=192, extend=64):
        """
        Initialize the Video Expander with UNetGenerator model.
        
        Args:
            model_path: Path to the model checkpoint
            device: Device to use (cuda/mps/cpu). Auto-detected if None.
            image_size: Size to resize input frames to (default: 192)
            extend: Extension size on each side (default: 64)
        """
        # Auto-detect best device
        if device is None:
            if torch.cuda.is_available():
                self.device = torch.device('cuda')
            elif torch.backends.mps.is_available():
                self.device = torch.device('mps')
                print("Accelerated with macOS Metal Performance Shaders (MPS)")
            else:
                self.device = torch.device('cpu')
        else:
            self.device = torch.device(device)
            
        print(f"Using device: {self.device}")
        
        # Model parameters
        self.S = int(image_size)  # Input size (e.g., 192)
        self.n = int(extend)      # Extension size (e.g., 64)
        self.Hc = self.Wc = self.S + self.n  # Canvas size (e.g., 256)
        
        # Load model
        self.model = UNetGenerator(in_ch=4, out_ch=3, ngf=64).to(self.device)
        self._safe_load_state(model_path)
        self.model.eval()
        
        # Transform to resize frames to SxS
        self.to_S = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((self.S, self.S), interpolation=transforms.InterpolationMode.BICUBIC),
            transforms.ToTensor()
        ])
        
        print(f"Model loaded: input={self.S}x{self.S}, output={self.Hc}x{self.Wc}")
    
    def _safe_load_state(self, ckpt_path):
        """Load model checkpoint with fallback to latest checkpoint."""
        if not os.path.isfile(ckpt_path):
            cand = sorted(Path("checkpoints").glob("G_epoch_*.*"))
            if not cand:
                raise FileNotFoundError("No generator checkpoint found in --checkpoint or ./checkpoints/")
            ckpt_path = str(cand[-1])
            print(f"Using checkpoint: {ckpt_path}")
        
        try:
            state = torch.load(ckpt_path, map_location=self.device, weights_only=True)
        except TypeError:
            state = torch.load(ckpt_path, map_location=self.device)
        
        if isinstance(state, dict) and "state_dict" in state:
            state = state["state_dict"]
        
        missing, unexpected = self.model.load_state_dict(state, strict=False)
        if missing or unexpected:
            print("[Warn] load_state_dict mismatches -> missing:", missing, " unexpected:", unexpected)
    
    def infer_frame(self, frame_bgr):
        """
        Process a single frame: resize to SxS, expand to (S+n)x(S+n).
        
        Args:
            frame_bgr: Input frame in BGR format (OpenCV format)
            
        Returns:
            Expanded frame in BGR format
        """
        # Convert BGR to RGB and resize to SxS
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img_S = self.to_S(frame_rgb).unsqueeze(0).to(self.device)
        
        # Build canvas and mask
        canvas, mask = build_center_canvas_and_mask(img_S, self.S, self.Hc, self.Wc, self.device)
        
        # Forward through model with auto-snap
        final = forward_with_auto_snap(
            self.model, canvas, mask, 
            multiples=(64, 128, 256, 512), 
            pad_mode_canvas="reflect"
        )
        
        # Convert back to BGR
        out_rgb = (final.squeeze(0).permute(1, 2, 0).clamp(0, 1).cpu().numpy() * 255.0).round().astype("uint8")
        out_bgr = cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR)
        
        return out_bgr
    
    def process_video(self, input_path, expanded_output_path, resized_original_output_path, 
                     frames_count=None, restore_size=False, progress_callback=None):
        """
        Process entire video with frame sampling support.
        
        Args:
            input_path: Path to input video
            expanded_output_path: Path to save expanded video
            resized_original_output_path: Path to save resized original video
            frames_count: Frames sampled per second AND output fps (None = use all frames)
            restore_size: Whether to restore to original aspect ratio after expansion
            progress_callback: Optional callback function(current, total, message) for progress updates
        """
        # Check input file
        if not os.path.exists(input_path):
            print(f"Error: File not found '{input_path}'")
            return

        # Define temporary files for OpenCV
        temp_expanded_cv = expanded_output_path.replace(".mp4", "_cv_temp.mp4")
        temp_resized_cv = resized_original_output_path.replace(".mp4", "_cv_temp.mp4")

        # Define temporary files for FFmpeg (must end with .mp4)
        temp_expanded_final = expanded_output_path.replace(".mp4", "_part.mp4")
        temp_resized_final = resized_original_output_path.replace(".mp4", "_part.mp4")

        cap = cv2.VideoCapture(input_path)
        W0 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        H0 = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_cnt = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        
        # Calculate output dimensions
        scale_h = H0 / self.S
        scale_w = W0 / self.S
        if restore_size:
            out_h = int(round(self.Hc * scale_h))
            out_w = int(round(self.Wc * scale_w))
        else:
            out_h = self.Hc
            out_w = self.Hc
        
        # Determine output FPS
        if frames_count is not None:
            target_fps = max(1, int(frames_count))
            duration_ms = (frame_cnt / max(1e-6, src_fps)) * 1000.0
            interval_ms = 1000.0 / target_fps
            num_slots = int(duration_ms / interval_ms) + 1
            use_sampling = True
        else:
            target_fps = src_fps
            num_slots = frame_cnt
            use_sampling = False
        
        # OpenCV Writers
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_expanded = cv2.VideoWriter(temp_expanded_cv, fourcc, target_fps, (out_w, out_h))
        out_resized_original = cv2.VideoWriter(temp_resized_cv, fourcc, target_fps, (self.S, self.S))
        
        print(f"Processing: {input_path}")
        print(f"Input: {W0}x{H0} @ {src_fps:.2f}fps, {frame_cnt} frames")
        print(f"Output: {out_w}x{out_h} @ {target_fps:.2f}fps")
        
        # Total steps: frame processing (80%) + FFmpeg conversion (20%)
        total_steps = num_slots + int(num_slots * 0.25)  # Add 25% for FFmpeg
        kept = 0
        
        if use_sampling:
            # Time-based sampling
            for i in range(num_slots):
                t_ms = i * interval_ms
                cap.set(cv2.CAP_PROP_POS_MSEC, t_ms)
                ok, frame_bgr = cap.read()
                if not ok:
                    continue
                
                # Process expanded frame
                result_frame = self.infer_frame(frame_bgr)
                
                # Resize if needed
                if restore_size:
                    result_frame = cv2.resize(result_frame, (out_w, out_h), 
                                            interpolation=cv2.INTER_CUBIC)
                
                out_expanded.write(result_frame)
                
                # Process original resized frame
                frame_resized = cv2.resize(frame_bgr, (self.S, self.S))
                out_resized_original.write(frame_resized)
                
                kept += 1
                
                # Update progress
                if progress_callback and i % 5 == 0:  # Update every 5 frames to reduce overhead
                    progress_callback(kept, total_steps, f"處理幀 {kept}/{num_slots}")
        else:
            # Process all frames
            for i in range(frame_cnt):
                ret, frame_bgr = cap.read()
                if not ret:
                    break
                
                # Process expanded frame
                result_frame = self.infer_frame(frame_bgr)
                
                # Resize if needed
                if restore_size:
                    result_frame = cv2.resize(result_frame, (out_w, out_h), 
                                            interpolation=cv2.INTER_CUBIC)
                
                out_expanded.write(result_frame)
                
                # Process original resized frame
                frame_resized = cv2.resize(frame_bgr, (self.S, self.S))
                out_resized_original.write(frame_resized)
                
                kept += 1
                
                # Update progress
                if progress_callback and i % 10 == 0:  # Update every 10 frames
                    progress_callback(kept, total_steps, f"處理幀 {kept}/{frame_cnt}")

        cap.release()
        out_expanded.release()
        out_resized_original.release()
        
        # Update progress: frame processing complete
        if progress_callback:
            progress_callback(num_slots, total_steps, "正在轉換影片格式...")
        
        # Convert to H.264 using FFmpeg
        print("Converting videos to H.264 for Web playback...")
        try:
            print(f"  - Converting Expanded Video to {temp_expanded_final}...")
            command_expanded = [
                "ffmpeg", "-y", "-i", temp_expanded_cv,
                "-vcodec", "libx264", "-pix_fmt", "yuv420p",
                "-an", 
                temp_expanded_final
            ]
            subprocess.run(command_expanded, check=True, capture_output=True)
            
            if progress_callback:
                progress_callback(num_slots + int(num_slots * 0.125), total_steps, "轉換第一個影片完成...")
            
            print(f"  - Converting Resized Original Video to {temp_resized_final}...")
            command_resized = [
                "ffmpeg", "-y", "-i", temp_resized_cv,
                "-vcodec", "libx264", "-pix_fmt", "yuv420p",
                "-an", 
                temp_resized_final
            ]
            subprocess.run(command_resized, check=True, capture_output=True)

            if progress_callback:
                progress_callback(total_steps - 1, total_steps, "正在完成...")

            # Atomic rename
            if os.path.exists(temp_expanded_final):
                os.rename(temp_expanded_final, expanded_output_path)
                print(f"  -> Renamed expanded video to: {expanded_output_path}")
            else:
                print(f"Error: FFmpeg output missing: {temp_expanded_final}")
                
            if os.path.exists(temp_resized_final):
                os.rename(temp_resized_final, resized_original_output_path)
                print(f"  -> Renamed resized video to: {resized_original_output_path}")
            else:
                print(f"Error: FFmpeg output missing: {temp_resized_final}")

            # Clean up OpenCV temp files
            if os.path.exists(temp_expanded_cv): 
                os.remove(temp_expanded_cv)
            if os.path.exists(temp_resized_cv): 
                os.remove(temp_resized_cv)
                
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg failed with return code {e.returncode}")
            print(f"stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
            raise e
        except Exception as e:
            print(f"Video processing failed: {e}")
            import traceback
            traceback.print_exc()
            raise

        print(f"Done! Processed {kept} frames at {target_fps:.2f} FPS")


if __name__ == "__main__":
    # Test the VideoExpander
    INPUT_FILE = "input_video.mp4" 
    EXPANDED_FILE = "output_expanded.mp4"
    RESIZED_FILE = "output_resized.mp4"
    MODEL_PATH = "checkpoints/G_epoch_010.pt"
    
    if os.path.exists(INPUT_FILE):
        expander = VideoExpander(model_path=MODEL_PATH, image_size=192, extend=64)
        expander.process_video(INPUT_FILE, EXPANDED_FILE, RESIZED_FILE)
    else:
        print(f"Please prepare test video: {INPUT_FILE}")