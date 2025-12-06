// frontend/src/App.jsx
import { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState('idle'); 
  const [videoUrls, setVideoUrls] = useState({ original: '', processed: '' });
  const [progress, setProgress] = useState(0); 
  const [progressMessage, setProgressMessage] = useState('');
  const [error, setError] = useState(null);
  const [videoList, setVideoList] = useState([]);

  // Refs
  const vid1Ref = useRef(null);
  const vid2Ref = useRef(null);
  const isSyncing = useRef(false);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatus('idle');
      setProgress(0);
      setError(null);
      setVideoUrls({ original: '', processed: '' });
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("請先選擇一個影片檔案 📂");
      return;
    }
    
    setStatus('uploading');
    setError(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      // 注意：如果你已經部署到 Server，這裡的路徑要改成 Server IP
      // 如果是 Docker 本機跑，localhost 沒問題
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) throw new Error("上傳失敗，請檢查後端服務");

      const data = await response.json();
      setTaskId(data.task_id);
      setVideoUrls({
        original: data.original_video_url,
        processed: data.processed_video_url
      });
      setStatus('processing');
      
    } catch (err) {
      console.error(err);
      setError(err.message);
      setStatus('idle');
    }
  };

  // Polling Status with Real Progress
  useEffect(() => {
    let intervalId;
    if (status === 'processing' && taskId) {
      intervalId = setInterval(async () => {
        try {
          const res = await fetch(`http://localhost:8000/status/${taskId}`);
          const data = await res.json();
          
          // 使用後端回傳的真實進度
          if (data.progress !== undefined) {
            setProgress(data.progress);
          }
          if (data.message) {
            setProgressMessage(data.message);
          }

          if (data.status === 'completed') {
            setStatus('completed');
            setProgress(100);
            setProgressMessage('處理完成！');
            clearInterval(intervalId);
          } else if (data.status === 'error') {
            setError(data.message || '處理失敗');
            setStatus('idle');
            clearInterval(intervalId);
          }
        } catch (err) {
          console.error("Status check failed", err);
        }
      }, 1000); // 更頻繁更新 (1秒)
    }
    return () => clearInterval(intervalId);
  }, [status, taskId]);

  // Fetch video list on mount and when processing completes
  useEffect(() => {
    fetchVideoList();
    // Refresh list every 10 seconds
    const listInterval = setInterval(fetchVideoList, 10000);
    return () => clearInterval(listInterval);
  }, []);

  // Also refresh when a video completes
  useEffect(() => {
    if (status === 'completed') {
      fetchVideoList();
    }
  }, [status]);

  const fetchVideoList = async () => {
    try {
      const res = await fetch('http://localhost:8000/videos/list');
      const data = await res.json();
      setVideoList(data.videos || []);
    } catch (err) {
      console.error("Failed to fetch video list", err);
    }
  };

  const loadDemoVideo = (video) => {
    setVideoUrls({
      original: video.original_url,
      processed: video.expanded_url
    });
    setStatus('completed');
    setProgress(100);
    setTaskId(video.task_id);
  };

  const deleteVideo = async (taskId, event) => {
    event.stopPropagation(); // Prevent triggering loadDemoVideo
    
    if (!confirm(`確定要刪除影片 ${taskId} 嗎？`)) {
      return;
    }
    
    try {
      const response = await fetch(`http://localhost:8000/videos/${taskId}`, {
        method: 'DELETE',
      });
      const result = await response.json();
      
      if (result.success) {
        // Refresh the video list
        fetchVideoList();
        
        // Clear current videos if they were deleted
        if (taskId === taskId) {
          setVideoUrls({ original: '', processed: '' });
          setStatus('idle');
          setProgress(0);
        }
      } else {
        alert(`刪除失敗: ${result.error}`);
      }
    } catch (error) {
      console.error('Error deleting video:', error);
      alert('刪除影片時發生錯誤');
    }
  };

  // --- Sync Logic ---
  const safePlay = async (videoElem) => {
    try {
      if (videoElem.paused) await videoElem.play();
    } catch (err) { /* ignore abort error */ }
  };

  const syncFunc = (action, source, target) => {
    if (isSyncing.current || !target.current) return;
    isSyncing.current = true;

    if (action === 'play') safePlay(target.current);
    else if (action === 'pause' && !target.current.paused) target.current.pause();
    else if (action === 'time') {
      if (Math.abs(target.current.currentTime - source.current.currentTime) > 0.1) {
        target.current.currentTime = source.current.currentTime;
      }
    }
    isSyncing.current = false;
  };
  // ------------------

  return (
    <div className="app-wrapper">
      {/* Main Content */}
      <div className="container">
        <header>
          <h1>AI Video Outpainting</h1>
          <p className="subtitle">基於 GAN 模型的視訊邊緣生成與擴展技術</p>
        </header>
        
        {/* 上傳區塊：只有在還沒完成時顯示，或者完成後想重新上傳 */}
      <div className="upload-card">
        <div className="file-input-wrapper">
          <span className="upload-icon">☁️</span>
          <p>{file ? `已選擇: ${file.name}` : "點擊或拖曳影片至此 (MP4, MOV)"}</p>
          <input type="file" accept="video/*" onChange={handleFileChange} />
        </div>
        
        <button 
          className="primary-btn"
          onClick={handleUpload} 
          disabled={!file || status === 'uploading' || status === 'processing'}
        >
          {status === 'uploading' ? '上傳中...' : status === 'processing' ? 'AI 運算中...' : '開始生成'}
        </button>

        {error && <div className="error-msg">{error}</div>}
      </div>

      {/* 進度條區塊 */}
      {status === 'processing' && (
        <div className="progress-container">
          <p style={{marginBottom: '10px'}}>{progressMessage || '正在進行畫面擴充與修復...'}</p>
          <div className="progress-bar-bg">
            <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
          </div>
          <p style={{fontSize: '0.8rem', color: '#666', marginTop: '5px'}}>{Math.round(progress)}%</p>
        </div>
      )}

      {/* 結果區塊 */}
      {status === 'completed' && (
        <div className="result-section">
          <div style={{textAlign: 'center', marginBottom: '20px'}}>
            <h2 style={{margin: 0}}>Processing Complete</h2>
            <p style={{color: 'var(--accent-color)'}}>✨ 擴展成功</p>
          </div>
          
          <div className="video-grid">
            <div className="video-card">
              <div className="video-label">Input (192x192)</div>
              <video 
                ref={vid1Ref}
                src={videoUrls.original} 
                controls 
                muted
                style={{width: '192px', height: '192px', objectFit: 'contain'}}
                onPlay={() => syncFunc('play', vid1Ref, vid2Ref)}
                onPause={() => syncFunc('pause', vid1Ref, vid2Ref)}
                onTimeUpdate={() => syncFunc('time', vid1Ref, vid2Ref)}
                onSeeking={() => syncFunc('time', vid1Ref, vid2Ref)}
              />
            </div>
            <div className="video-card">
              <div className="video-label" style={{color: 'var(--accent-color)'}}>Output (256x256)</div>
              <video 
                className="video-expanded"
                ref={vid2Ref}
                src={videoUrls.processed} 
                controls 
                muted
                style={{width: '256px', height: '256px', objectFit: 'contain'}}
                onPlay={() => syncFunc('play', vid2Ref, vid1Ref)}
                onPause={() => syncFunc('pause', vid2Ref, vid1Ref)}
                onTimeUpdate={() => syncFunc('time', vid2Ref, vid1Ref)}
                onSeeking={() => syncFunc('time', vid2Ref, vid1Ref)}
              />
            </div>
          </div>
          
          <div style={{textAlign: 'center', marginTop: '30px'}}>
            <button className="primary-btn" onClick={() => {
              setStatus('idle');
              setFile(null);
              setVideoUrls({original: '', processed: ''});
            }}>
              處理新的影片
            </button>
          </div>
        </div>
      )}
      </div>

      {/* Sidebar */}
      <div className="sidebar">
        <h3>📹 處理記錄</h3>
        <div className="video-list">
          {videoList.length === 0 ? (
            <p className="empty-message">尚無處理記錄</p>
          ) : (
            videoList.map((video) => (
              <div 
                key={video.task_id} 
                className="video-item"
                onClick={() => loadDemoVideo(video)}
              >
                <div className="video-item-content">
                  <div>
                    <div className="video-item-label">
                      {new Date(video.timestamp * 1000).toLocaleString('zh-TW', {
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </div>
                    <div className="video-item-id">ID: {video.task_id.slice(0, 8)}...</div>
                  </div>
                  <button
                    className="delete-btn"
                    onClick={(e) => deleteVideo(video.task_id, e)}
                    title="刪除影片"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default App;