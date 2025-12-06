# backend/main.py
import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from core_logic import VideoExpander 

app = FastAPI()

# --- 設定 CORS (允許前端存取) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開發階段允許所有來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 設定路徑 ---
UPLOAD_DIR = "uploads"
RESULT_DIR = "results"
MODEL_PATH = "checkpoints/G_epoch_063.pt"  # Updated to match test_video.py checkpoint naming

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs("checkpoints", exist_ok=True) # 確保 checkpoints 資料夾存在

# 初始化模型 (全域變數，啟動時載入一次)
# device=None 會自動偵測: CUDA > MPS > CPU
# image_size=192, extend=64 matches test_video.py defaults
expander = VideoExpander(model_path=MODEL_PATH, device=None, image_size=192, extend=64) 

# 全域進度追蹤字典 {task_id: {"progress": 0-100, "status": "processing"/"completed"/"error", "message": "..."}}
progress_tracker = {}

# --- 靜態檔案服務 ---
app.mount("/results", StaticFiles(directory=RESULT_DIR), name="results")
# original_uploads 這裡不需要 mount 了，因為 Resize 過的檔案也會放在 results 裡

# Root path for testing
@app.get("/")
def read_root():
    return {"message": "Video Expansion API is running! Access /docs for API details."}


@app.get("/videos/list")
def list_videos():
    """
    List all processed video pairs in the results directory.
    Returns array of {task_id, original_url, expanded_url, timestamp}
    """
    try:
        videos = []
        if not os.path.exists(RESULT_DIR):
            os.makedirs(RESULT_DIR, exist_ok=True)
            return {"videos": []}
        
        files = os.listdir(RESULT_DIR)
        task_ids = set()
        
        # Extract unique task IDs from filenames
        for filename in files:
            if "_expanded.mp4" in filename:
                task_id = filename.replace("_expanded.mp4", "")
                task_ids.add(task_id)
        
        # Build video pairs
        for task_id in sorted(task_ids, reverse=True):  # Most recent first
            expanded_file = f"{task_id}_expanded.mp4"
            original_file = f"{task_id}_original_192x192.mp4"
            
            expanded_path = os.path.join(RESULT_DIR, expanded_file)
            original_path = os.path.join(RESULT_DIR, original_file)
            
            if os.path.exists(expanded_path) and os.path.exists(original_path):
                # Get file modification time for sorting
                timestamp = os.path.getmtime(expanded_path)
                
                videos.append({
                    "task_id": task_id,
                    "original_url": f"http://localhost:8000/results/{original_file}",
                    "expanded_url": f"http://localhost:8000/results/{expanded_file}",
                    "timestamp": timestamp
                })
        
        # Sort by timestamp (newest first)
        videos.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {"videos": videos}
    
    except Exception as e:
        print(f"Error listing videos: {e}")
        import traceback
        traceback.print_exc()
        return {"videos": [], "error": str(e)}


@app.delete("/videos/{task_id}")
def delete_video(task_id: str):
    """
    Delete a specific processed video pair.
    
    Args:
        task_id: The task ID of the video to delete
        
    Returns:
        {"success": True/False, "deleted": [...files...] or "error": "..."}
    """
    try:
        expanded_file = f"{task_id}_expanded.mp4"
        original_file = f"{task_id}_original_192x192.mp4"
        
        expanded_path = os.path.join(RESULT_DIR, expanded_file)
        original_path = os.path.join(RESULT_DIR, original_file)
        
        deleted_files = []
        
        if os.path.exists(expanded_path):
            os.remove(expanded_path)
            deleted_files.append(expanded_file)
        
        if os.path.exists(original_path):
            os.remove(original_path)
            deleted_files.append(original_file)
        
        if deleted_files:
            print(f"Deleted video pair: {task_id}")
            return {"success": True, "deleted": deleted_files}
        else:
            return {"success": False, "error": f"Video not found: {task_id}"}
    
    except Exception as e:
        print(f"Error deleting video {task_id}: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def process_video_task(task_id: str, input_path: str, expanded_output_path: str, 
                       resized_original_output_path: str, frames_count: int = None, 
                       restore_size: bool = False):
    """
    背景執行的任務函數
    
    Args:
        task_id: Unique task identifier
        input_path: Path to input video
        expanded_output_path: Path to save expanded video
        resized_original_output_path: Path to save resized original
        frames_count: Frames sampled per second (None = use all frames)
        restore_size: Whether to restore to original aspect ratio
    """
    print(f"[{task_id}] 開始處理影片...")
    progress_tracker[task_id] = {"progress": 0, "status": "processing", "message": "初始化..."}
    
    try:
        # 呼叫核心邏輯，傳入所有參數和進度回調
        def progress_callback(current, total, message=""):
            progress = int((current / total) * 100) if total > 0 else 0
            progress_tracker[task_id] = {
                "progress": progress,
                "status": "processing",
                "message": message or f"處理中 {current}/{total} 幀"
            }
        
        expander.process_video(
            input_path, 
            expanded_output_path, 
            resized_original_output_path,
            frames_count=frames_count,
            restore_size=restore_size,
            progress_callback=progress_callback
        )
        
        progress_tracker[task_id] = {"progress": 100, "status": "completed", "message": "處理完成！"}
        print(f"[{task_id}] 處理完成！")
        
        # Keep the original uploaded file for demo purposes (don't delete)
        # if os.path.exists(input_path):
        #     os.remove(input_path)
        #     print(f"[{task_id}] 原始上傳影片已刪除: {input_path}")
    except Exception as e:
        progress_tracker[task_id] = {"progress": 0, "status": "error", "message": f"錯誤: {str(e)}"}
        print(f"[{task_id}] 處理失敗: {e}")
        import traceback
        traceback.print_exc()

@app.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    frames_count: int = None,  # Optional: frames sampled per second
    restore_size: bool = False  # Optional: restore to original aspect ratio
):
    """
    Upload and process a video.
    
    Args:
        file: Video file (mp4, mov, avi)
        frames_count: Optional - frames sampled per second (also sets output fps). 
                     If None, processes all frames at original fps.
        restore_size: Optional - restore to original aspect ratio after expansion.
                     Default False keeps square output.
    """
    if not file.filename.lower().endswith((".mp4", ".mov", ".avi")):
        raise HTTPException(status_code=400, detail="只接受影片檔案 (mp4, mov, avi)")

    # 1. 產生唯一 ID
    task_id = str(uuid.uuid4())
    original_uploaded_filename = f"{task_id}_original_uploaded.mp4" # 原始上傳檔
    input_path = os.path.join(UPLOAD_DIR, original_uploaded_filename)
    
    # 擴大後的影片檔
    expanded_output_filename = f"{task_id}_expanded.mp4" 
    expanded_output_path = os.path.join(RESULT_DIR, expanded_output_filename)

    # Resize 過的原始影片檔 (192x192 用於前端比較)
    resized_original_output_filename = f"{task_id}_original_192x192.mp4"
    resized_original_output_path = os.path.join(RESULT_DIR, resized_original_output_filename)

    # 2. 儲存上傳的影片
    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"儲存上傳檔案失敗: {e}")

    # 3. 初始化進度追蹤
    progress_tracker[task_id] = {"progress": 0, "status": "processing", "message": "上傳完成，準備處理..."}
    
    # 4. 加入背景任務 (with new parameters)
    background_tasks.add_task(
        process_video_task, 
        task_id, 
        input_path, 
        expanded_output_path, 
        resized_original_output_path,
        frames_count=frames_count,
        restore_size=restore_size
    )

    # 5. 回傳資訊給前端
    return {
        "task_id": task_id,
        "status": "processing",
        # 現在 original_video_url 指向的是 Resize 過的原始影片
        "original_video_url": f"http://localhost:8000/results/{resized_original_output_filename}",
        "processed_video_url": f"http://localhost:8000/results/{expanded_output_filename}",
        "params": {
            "frames_count": frames_count,
            "restore_size": restore_size
        }
    }

@app.get("/status/{task_id}")
def check_status(task_id: str):
    """
    檢查任務狀態和進度
    
    Returns:
        {
            "status": "processing" | "completed" | "error",
            "progress": 0-100,
            "message": "狀態訊息"
        }
    """
    # 如果有進度追蹤資訊，優先使用
    if task_id in progress_tracker:
        return progress_tracker[task_id]
    
    # Fallback: 檢查檔案是否存在（向下兼容）
    expanded_filename = f"{task_id}_expanded.mp4"
    expanded_path = os.path.join(RESULT_DIR, expanded_filename)
    
    original_resized_filename = f"{task_id}_original_192x192.mp4"
    original_resized_path = os.path.join(RESULT_DIR, original_resized_filename)
    
    expanded_exists = os.path.exists(expanded_path)
    resized_exists = os.path.exists(original_resized_path)

    if expanded_exists and resized_exists:
        return {"status": "completed", "progress": 100, "message": "處理完成"}
    else:
        return {"status": "processing", "progress": 0, "message": "處理中..."}