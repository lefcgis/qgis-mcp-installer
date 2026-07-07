<#
.SYNOPSIS
    Firma el instalador .exe con tu certificado de firma de código.

.DESCRIPTION
    Usa Set-AuthenticodeSignature (nativo de PowerShell, no requiere el SDK de
    Windows / signtool). Añade sello de tiempo (timestamp) para que la firma siga
    siendo válida aunque el certificado caduque.

    NO incluye ningún certificado: tú aportas el TUYO, comprado a una Autoridad
    Certificadora (DigiCert, Sectigo, SSL.com, …) tras validar tu identidad.
    Un certificado autofirmado NO sirve para distribución pública: Windows no lo
    reconoce en otras máquinas y seguirá mostrando la advertencia de SmartScreen.

.PARAMETER ExePath
    Ruta al .exe a firmar (por defecto dist\qgis-mcp-installer.exe).

.PARAMETER PfxPath
    Ruta a tu certificado .pfx/.p12. Alternativa a -Thumbprint.

.PARAMETER Thumbprint
    Huella del certificado ya instalado en tu almacén (Cert:\CurrentUser\My).
    Úsalo con certificados EV en token de hardware.

.PARAMETER Password
    Contraseña del .pfx (si aplica).

.PARAMETER TimestampUrl
    Servidor de sello de tiempo RFC 3161.

.EXAMPLE
    # Con archivo .pfx
    .\sign.ps1 -PfxPath "C:\certs\mi-cert.pfx" -Password "****"

.EXAMPLE
    # Con certificado EV en token (ya visible en el almacén)
    .\sign.ps1 -Thumbprint "A1B2C3D4E5F6..."
#>
param(
    [string]$ExePath = "dist\qgis-mcp-installer.exe",
    [string]$PfxPath,
    [string]$Thumbprint,
    [string]$Password,
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ExePath)) {
    Write-Error "No existe el ejecutable: $ExePath. Constrúyelo con build_exe.py."
}

# --- Obtener el certificado ---
if ($PfxPath) {
    if (-not (Test-Path $PfxPath)) { Write-Error "No existe el .pfx: $PfxPath" }
    if ($Password) {
        $sec = ConvertTo-SecureString $Password -AsPlainText -Force
        $cert = Get-PfxCertificate -FilePath $PfxPath -Password $sec
    } else {
        $cert = Get-PfxCertificate -FilePath $PfxPath
    }
} elseif ($Thumbprint) {
    $cert = Get-Item "Cert:\CurrentUser\My\$Thumbprint" -ErrorAction SilentlyContinue
    if (-not $cert) { $cert = Get-Item "Cert:\LocalMachine\My\$Thumbprint" }
} else {
    Write-Error "Indica -PfxPath o -Thumbprint con tu certificado de firma."
}

Write-Host "Firmando $ExePath" -ForegroundColor Cyan
Write-Host "  Certificado: $($cert.Subject)"
Write-Host "  Sello de tiempo: $TimestampUrl"

$result = Set-AuthenticodeSignature -FilePath $ExePath -Certificate $cert `
    -HashAlgorithm SHA256 -TimestampServer $TimestampUrl

$statusColor = if ($result.Status -eq "Valid") { "Green" } else { "Yellow" }
Write-Host "  Estado: $($result.Status)" -ForegroundColor $statusColor

if ($result.Status -ne "Valid") {
    Write-Error "La firma no quedó válida: $($result.StatusMessage)"
}

# --- Publica el hash para que cualquiera lo verifique ---
$hash = (Get-FileHash $ExePath -Algorithm SHA256).Hash.ToLower()
Write-Host "`nSHA-256 del .exe firmado (publícalo junto a la descarga):" -ForegroundColor Cyan
Write-Host "  $hash"
