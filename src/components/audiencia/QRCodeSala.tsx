import { QRCodeSVG } from "qrcode.react";
export function QRCodeSala({
  url,
  code,
  onCopy,
}: {
  url: string;
  code: string;
  onCopy: () => void;
}) {
  return (
    <section className="audience-qr" aria-label="Entrada da sala">
      <QRCodeSVG
        value={url}
        size={210}
        bgColor="#edf5ff"
        fgColor="#07101d"
        level="M"
        includeMargin
      />
      <p>APONTE A CÂMERA</p>
      <strong>{code}</strong>
      <button type="button" onClick={onCopy}>
        Copiar link de participação
      </button>
      <small>O QR Code não contém a credencial do apresentador.</small>
    </section>
  );
}
