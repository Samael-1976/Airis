import { useRef, useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { useTranslation } from "@/contexts/TranslationContext"; // [NUOVO]
import { Button } from "@/components/ui/button";
import { Camera, Video, StopCircle, RefreshCw, Check, AlertTriangle, SwitchCamera } from "lucide-react";
import { getHeaders } from "@/lib/api";

interface CameraCaptureDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCapture: (file: File, type: "image" | "video") => void;
  serverUrl: string;
}

// AGGIUNTO 'export' QUI SOTTO
export const CameraCaptureDialog = ({ open, onOpenChange, onCapture, serverUrl }: CameraCaptureDialogProps) => {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [mode, setMode] = useState<"photo" | "video">("photo");
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [recordedChunks, setRecordedChunks] = useState<Blob[]>([]);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [capturedVideo, setCapturedVideo] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<"user" | "environment">("user"); 
  
  const [isBackendReady, setIsBackendReady] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const manageBackendResource = async () => {
      if (open) {
        setErrorMsg(null);
        try {
          console.log(t("camera_dialog.log_req_release"));
          await fetch(`${serverUrl}/api/camera/release`, { 
              method: 'POST',
              headers: getHeaders()
          });
          if (isMounted) setIsBackendReady(true);
        } catch (e) {
          console.error(t("camera_dialog.err_release"), e);
          if (isMounted) setErrorMsg(t("camera_dialog.err_backend"));
        }
      } else {
        if (isMounted) setIsBackendReady(false);
      }
    };

    manageBackendResource();

    return () => {
      isMounted = false;
      if (open) {
        console.log(t("camera_dialog.log_req_acquire"));
        fetch(`${serverUrl}/api/camera/acquire`, { 
            method: 'POST',
            headers: getHeaders()
        }).catch(e => console.error(e));
      }
    };
  }, [open, serverUrl]);

  useEffect(() => {
    if (!open || !isBackendReady) {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
        setStream(null);
      }
      return;
    }

    const isSecureContext = window.isSecureContext;
    if (!isSecureContext && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        setErrorMsg(t("camera_dialog.err_security"));
        return;
    }

    let localStream: MediaStream | null = null;

    const startLocalStream = async () => {
      try {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }

        await new Promise(resolve => setTimeout(resolve, 500));
        
        localStream = await navigator.mediaDevices.getUserMedia({ 
          video: { facingMode: facingMode }, 
          audio: mode === "video" 
        });
        
        setStream(localStream);
        setErrorMsg(null);
        if (videoRef.current) {
          videoRef.current.srcObject = localStream;
        }
      } catch (err: any) {
        console.error(t("camera_dialog.err_access_local"), err);
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            setErrorMsg(t("camera_dialog.err_permission"));
        } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
            setErrorMsg(t("camera_dialog.err_hardware"));
        } else {
            setErrorMsg(t("camera_dialog.err_generic", { message: err.message || err.name }));
        }
      }
    };

    startLocalStream();

    return () => {
      if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [isBackendReady, mode, open, facingMode]);

  const toggleCamera = () => {
      setFacingMode(prev => prev === "user" ? "environment" : "user");
  };

  const resetCapture = () => {
    setCapturedImage(null);
    setCapturedVideo(null);
    setRecordedChunks([]);
    setIsRecording(false);
    setErrorMsg(null);
  };

  const takePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext("2d");
      if (context) {
        if (facingMode === "user") {
            context.translate(canvas.width, 0);
            context.scale(-1, 1);
        }
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL("image/jpeg");
        setCapturedImage(dataUrl);
      }
    }
  };

  const startRecording = () => {
    if (stream) {
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: "video/webm" });
        const url = URL.createObjectURL(blob);
        setCapturedVideo(url);
        setRecordedChunks(chunks);
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const handleConfirm = () => {
    if (mode === "photo" && capturedImage) {
      fetch(capturedImage)
        .then(res => res.blob())
        .then(blob => {
          const file = new File([blob], `capture_${Date.now()}.jpg`, { type: "image/jpeg" });
          onCapture(file, "image");
          onOpenChange(false);
        });
    } else if (mode === "video" && recordedChunks.length > 0) {
      const blob = new Blob(recordedChunks, { type: "video/webm" });
      const file = new File([blob], `video_${Date.now()}.webm`, { type: "video/webm" });
      onCapture(file, "video");
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("camera_dialog.title")}</DialogTitle>
          <DialogDescription>
            {t("camera_dialog.description")}
          </DialogDescription>
        </DialogHeader>

        <div className="relative aspect-video bg-black rounded-lg overflow-hidden flex items-center justify-center group">
          {errorMsg ? (
              <div className="text-center p-4 text-red-400">
                  <AlertTriangle className="w-10 h-10 mx-auto mb-2" />
                  <p className="text-sm font-medium">{errorMsg}</p>
              </div>
          ) : (
              <>
                  {!capturedImage && !capturedVideo && (
                    <>
                        <video 
                            ref={videoRef} 
                            autoPlay 
                            playsInline 
                            muted 
                            className={`w-full h-full object-cover ${facingMode === 'user' ? 'scale-x-[-1]' : ''}`} 
                        />
                        <Button 
                            variant="secondary" 
                            size="icon" 
                            className="absolute top-2 right-2 bg-black/50 hover:bg-black/70 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={toggleCamera}
                            disabled={isRecording}
                        >
                            <SwitchCamera className="w-5 h-5" />
                        </Button>
                    </>
                  )}
                  {capturedImage && (
                    <img src={capturedImage} alt={t("camera_dialog.alt_captured")} className="w-full h-full object-contain" />
                  )}
                  {capturedVideo && (
                    <video src={capturedVideo} controls className="w-full h-full object-contain" />
                  )}
              </>
          )}
          <canvas ref={canvasRef} className="hidden" />
        </div>

        <div className="flex justify-center gap-4 py-2">
            {!capturedImage && !capturedVideo && !errorMsg && (
                <>
                    <Button 
                        variant={mode === "photo" ? "default" : "outline"} 
                        onClick={() => setMode("photo")}
                        disabled={isRecording}
                    >
                        {t("camera_dialog.photo")}
                    </Button>
                    <Button 
                        variant={mode === "video" ? "default" : "outline"} 
                        onClick={() => setMode("video")}
                        disabled={isRecording}
                    >
                        {t("camera_dialog.video")}
                    </Button>
                </>
            )}
        </div>

        <DialogFooter className="sm:justify-between">
          <div className="flex gap-2">
             {(capturedImage || capturedVideo) && (
                <Button variant="outline" onClick={resetCapture}>
                    <RefreshCw className="w-4 h-4 mr-2" /> {t("camera_dialog.retake")}
                </Button>
             )}
          </div>

          <div className="flex gap-2 justify-center w-full sm:w-auto">
            {!capturedImage && !capturedVideo && !errorMsg ? (
                mode === "photo" ? (
                    <Button onClick={takePhoto} className="w-full sm:w-auto" disabled={!isBackendReady}>
                        <Camera className="w-4 h-4 mr-2" /> {t("camera_dialog.capture")}
                    </Button>
                ) : (
                    !isRecording ? (
                        <Button onClick={startRecording} className="w-full sm:w-auto bg-red-600 hover:bg-red-700" disabled={!isBackendReady}>
                            <Video className="w-4 h-4 mr-2" /> {t("camera_dialog.record")}
                        </Button>
                    ) : (
                        <Button onClick={stopRecording} className="w-full sm:w-auto bg-red-600 hover:bg-red-700 animate-pulse">
                            <StopCircle className="w-4 h-4 mr-2" /> {t("camera_dialog.stop")}
                        </Button>
                    )
                )
            ) : (
                (capturedImage || capturedVideo) && (
                    <Button onClick={handleConfirm} className="w-full sm:w-auto bg-green-600 hover:bg-green-700">
                        <Check className="w-4 h-4 mr-2" /> {t("camera_dialog.use_this")}
                    </Button>
                )
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};