import React, { useState, useEffect, useRef } from "react";
import api from "../services/api";
import { Camera, CameraOff, Video, AlertCircle, Heart } from "lucide-react";

const EmotionCapture = () => {
  const [streamActive, setStreamActive] = useState(false);
  const [emotion, setEmotion] = useState("Not Started");
  const [confidence, setConfidence] = useState(0.0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const intervalRef = useRef(null);

  const startCamera = async () => {
    try {
      setError("");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 400, height: 300 },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setStreamActive(true);
      }
    } catch (err) {
      console.error(err);
      setError("Webcam permissions were denied or no camera device found.");
    }
  };

  const stopCamera = () => {
    if (videoRef.current?.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach((track) => track.stop());
      videoRef.current.srcObject = null;
    }
    setStreamActive(false);
    clearInterval(intervalRef.current);
    setEmotion("Stopped");
  };

  const captureFrame = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    setLoading(true);

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    // Draw video frame to hidden canvas
    canvas.width = video.videoWidth || 400;
    canvas.height = video.videoHeight || 300;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Get base64 string (including data prefix)
    const base64Image = canvas.toDataURL("image/jpeg");

    try {
      const res = await api.post("/api/emotions/capture/", {
        image: base64Image,
      });
      if (res.status === 200) {
        setEmotion(res.data.emotion);
        setConfidence(res.data.confidence);
      }
    } catch (err) {
      console.error("Emotion analysis failed", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (streamActive) {
      // Capture frame immediately, then every 10 seconds
      captureFrame();
      intervalRef.current = setInterval(captureFrame, 10000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [streamActive]);

  useEffect(() => {
    return () => {
      // Clean up camera on unmount
      if (videoRef.current?.srcObject) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach((track) => track.stop());
      }
    };
  }, []);

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <Heart size={28} className="text-red-500 animate-pulse" />
          Student well-being tracking
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          SkillBuddy monitors stress levels and student emotions to prevent academic anxiety.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        {/* Camera Feed */}
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="aspect-[4/3] bg-slate-950/90 rounded-xl overflow-hidden relative border border-slate-800/80 flex items-center justify-center">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className={`w-full h-full object-cover ${!streamActive && "hidden"}`}
            />
            {!streamActive && (
              <div className="text-center space-y-2 text-slate-500">
                <CameraOff size={48} className="mx-auto text-slate-700" />
                <p className="text-xs">Camera is turned off</p>
              </div>
            )}
            {loading && (
              <div className="absolute top-3 right-3 bg-blue-600/20 border border-blue-500/20 text-blue-400 text-xs px-2.5 py-1 rounded-full animate-pulse">
                Analyzing Sentiment...
              </div>
            )}
          </div>

          <div className="flex gap-4">
            {!streamActive ? (
              <button
                onClick={startCamera}
                className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-xl py-3 text-sm flex items-center justify-center gap-2 transition-colors shadow-lg shadow-blue-500/10"
              >
                <Video size={18} />
                Start Webcam Feed
              </button>
            ) : (
              <button
                onClick={stopCamera}
                className="flex-1 bg-red-600/10 hover:bg-red-600/20 border border-red-500/20 text-red-400 font-medium rounded-xl py-3 text-sm flex items-center justify-center gap-2 transition-colors"
              >
                <CameraOff size={18} />
                Stop Feed
              </button>
            )}
          </div>
        </div>

        {/* Emotion status results */}
        <div className="space-y-6">
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 shadow-xl">
            <h3 className="text-lg font-bold text-white mb-6">Welfare Monitoring</h3>
            <div className="space-y-6">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Detected Sentiment</p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-2xl font-black text-white">{emotion}</span>
                  {streamActive && (
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
                  )}
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Confidence Score</p>
                <h4 className="text-xl font-bold text-slate-200 mt-1">{(confidence * 100).toFixed(1)}%</h4>
              </div>

              <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 text-xs text-slate-400 leading-relaxed">
                When active, your webcam snapshot is analyzed periodically using AI. If consistent signs of stress or anxiety are detected, your academic counselor and parents are notified automatically.
              </div>
            </div>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-xl p-4 flex items-center gap-2">
              <AlertCircle size={18} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>
      </div>

      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
};

export default EmotionCapture;
