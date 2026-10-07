"use client";

import { BrowserQRCodeReader } from "@zxing/browser";
import { Camera, Keyboard, ScanLine, ShieldAlert, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export default function Scanner({
  onScan,
  disabled = false,
  buttonLabel = "Escanear QR",
}: {
  onScan: (payload: string) => void | Promise<void>;
  disabled?: boolean;
  buttonLabel?: string;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const controlsRef = useRef<{ stop: () => void } | null>(null);
  const processingRef = useRef(false);
  const onScanRef = useRef(onScan);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [manual, setManual] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    onScanRef.current = onScan;
  }, [onScan]);

  async function startCamera() {
    if (disabled || cameraOpen) return;
    setError("");
    processingRef.current = false;
    setProcessing(false);

    if (typeof window !== "undefined" && !window.isSecureContext) {
      setError("La cámara requiere HTTPS. Abrí ReciclaTrace desde la URL móvil segura (https://...).");
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Este navegador no ofrece acceso a cámara. Probá con Chrome o Safari actualizado.");
      return;
    }

    setCameraOpen(true);
  }

  function stopCamera() {
    controlsRef.current?.stop();
    controlsRef.current = null;
    processingRef.current = false;
    setProcessing(false);
    setCameraOpen(false);
  }

  useEffect(() => {
    if (!cameraOpen) return;

    let cancelled = false;
    document.body.classList.add("scanner-open");

    const timer = window.setTimeout(async () => {
      try {
        const reader = new BrowserQRCodeReader();
        const controls = await reader.decodeFromConstraints(
          {
            audio: false,
            video: {
              facingMode: { ideal: "environment" },
              width: { ideal: 1920 },
              height: { ideal: 1080 },
            },
          },
          videoRef.current!,
          async (result) => {
            if (!result || processingRef.current || cancelled) return;

            processingRef.current = true;
            setProcessing(true);
            controlsRef.current?.stop();
            const stream = videoRef.current?.srcObject;
            if (stream instanceof MediaStream) {
              stream.getTracks().forEach(track => track.stop());
            }
            controlsRef.current = null;

            try {
              await Promise.resolve(onScanRef.current(result.getText()));
            } finally {
              if (!cancelled) {
                setCameraOpen(false);
                setProcessing(false);
                processingRef.current = false;
              }
            }
          }
        );

        if (cancelled) {
          controls.stop();
          return;
        }
        controlsRef.current = controls;
      } catch {
        if (!cancelled) {
          setCameraOpen(false);
          setError("No se pudo abrir la cámara. Verificá el permiso de cámara para este sitio.");
        }
      }
    }, 80);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      controlsRef.current?.stop();
      controlsRef.current = null;
      document.body.classList.remove("scanner-open");
    };
  }, [cameraOpen]);

  useEffect(() => () => controlsRef.current?.stop(), []);

  return (
    <div className="scanner-card">
      <div className="scanner-toolbar">
        <button className="primary-btn" onClick={startCamera} disabled={disabled || cameraOpen}>
          <Camera size={17}/> {buttonLabel}
        </button>
        <div className="scanner-hint"><ScanLine size={16}/> Detección automática · una lectura = una bolsa</div>
      </div>

      {error && <div className="alert error"><ShieldAlert size={16}/>{error}</div>}

      <div className="manual-scan">
        <Keyboard size={17}/>
        <input
          value={manual}
          onChange={e => setManual(e.target.value)}
          placeholder="Ingreso manual del contenido del QR"
          disabled={disabled}
        />
        <button
          className="ghost-btn"
          disabled={!manual.trim() || disabled}
          onClick={async () => {
            const value = manual.trim();
            setManual("");
            await Promise.resolve(onScan(value));
          }}
        >
          Registrar
        </button>
      </div>

      {cameraOpen && (
        <div className="scanner-fullscreen" role="dialog" aria-modal="true" aria-label="Escáner de código QR">
          <video ref={videoRef} muted playsInline autoPlay />
          <div className="scanner-shade"/>

          <div className="scanner-topbar">
            <div>
              <b>Escanear QR</b>
              <span>Apuntá la cámara al código. La lectura es automática.</span>
            </div>
            <button className="scanner-close" onClick={stopCamera} aria-label="Cerrar cámara">
              <X size={24}/>
            </button>
          </div>

          <div className="scanner-target" aria-hidden="true">
            <span className="corner tl"/><span className="corner tr"/>
            <span className="corner bl"/><span className="corner br"/>
            <div className="scan-beam"/>
          </div>

          <div className="scanner-bottom-hint">
            {processing ? "QR detectado · registrando..." : "No hace falta sacar una foto ni presionar Capturar"}
          </div>
        </div>
      )}
    </div>
  );
}
