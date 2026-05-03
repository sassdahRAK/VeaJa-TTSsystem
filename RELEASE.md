# Veaja — Release & Code Signing Guide

How to build, sign, and distribute Veaja on each platform.

---

## Quick summary

| Platform | Signing tool | Certificate cost | Required? |
|---|---|---|---|
| Linux | GPG (self-signed) | Free | No — optional |
| Windows | signtool.exe | $100–$500/yr (OV cert) | No — but SmartScreen warns |
| macOS | codesign + notarytool | $99/yr (Apple Developer) | Yes — Gatekeeper blocks unsigned |

---

## Linux

### Build

```bash
chmod +x build_linux.sh
./build_linux.sh
# Output: dist/veaja-1.0.0-linux-x86_64.tar.gz
```

### Sign with GPG (optional but recommended)

GPG signing lets users verify the download is authentic and hasn't been tampered with.
It's free and doesn't require any certificate authority.

**Step 1 — Create your GPG key (one time only)**

```bash
gpg --full-generate-key
```

Choose:
- Key type: `RSA and RSA`
- Key size: `4096`
- Expiry: `2y` (2 years)
- Name: your real name
- Email: your email

**Step 2 — Export your public key so users can verify**

```bash
# Export to a file to share on your website / GitHub
gpg --armor --export your@email.com > veaja-public-key.asc

# Also upload to a public keyserver
gpg --keyserver keyserver.ubuntu.com --send-keys YOUR_KEY_ID
```

Find your key ID:
```bash
gpg --list-keys your@email.com
# Look for: pub   rsa4096 2024-01-01 [SC]
#                 ABCD1234EFGH5678...   ← this is your key ID
```

**Step 3 — Sign the release file**

```bash
cd dist
gpg --armor --detach-sign veaja-1.0.0-linux-x86_64.tar.gz
# Creates: veaja-1.0.0-linux-x86_64.tar.gz.asc
```

**Step 4 — Generate SHA256 checksum**

```bash
sha256sum veaja-1.0.0-linux-x86_64.tar.gz > veaja-1.0.0-linux-x86_64.tar.gz.sha256
```

**What to upload to GitHub Releases:**
```
veaja-1.0.0-linux-x86_64.tar.gz        ← the app
veaja-1.0.0-linux-x86_64.tar.gz.asc    ← GPG signature
veaja-1.0.0-linux-x86_64.tar.gz.sha256 ← checksum
veaja-public-key.asc                    ← your public key
```

**How users verify:**
```bash
# Import your public key
gpg --import veaja-public-key.asc

# Verify the signature
gpg --verify veaja-1.0.0-linux-x86_64.tar.gz.asc veaja-1.0.0-linux-x86_64.tar.gz
# Should say: Good signature from "Your Name <your@email.com>"

# Verify checksum
sha256sum -c veaja-1.0.0-linux-x86_64.tar.gz.sha256
```

---

## Windows

### Build

On a Windows machine with Python and the venv set up:

```cmd
venv\Scripts\activate
pip install pyinstaller
pyinstaller veaja.spec --clean --noconfirm
```

Then package:
```cmd
cd dist
rename veaja veaja-1.0.0-windows-x64
powershell Compress-Archive veaja-1.0.0-windows-x64 veaja-1.0.0-windows-x64.zip
```

Or use Inno Setup with the included `installer.iss` to create a proper `.exe` installer.

### Sign with a self-signed certificate (free, for testing)

A self-signed certificate won't remove the SmartScreen warning but is useful for
internal distribution or testing the signing workflow.

**Step 1 — Create a self-signed certificate (PowerShell, run as Administrator)**

```powershell
$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject "CN=Veaja, O=YourName, C=KH" `
    -KeyUsage DigitalSignature `
    -FriendlyName "Veaja Code Signing" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -HashAlgorithm SHA256 `
    -NotAfter (Get-Date).AddYears(3)

# Export to PFX file (set a strong password)
Export-PfxCertificate `
    -Cert $cert `
    -FilePath "veaja-codesign.pfx" `
    -Password (ConvertTo-SecureString -String "YourPassword" -Force -AsPlainText)
```

**Step 2 — Sign the executable**

```cmd
signtool sign ^
    /f veaja-codesign.pfx ^
    /p YourPassword ^
    /fd SHA256 ^
    /tr http://timestamp.digicert.com ^
    /td SHA256 ^
    /v ^
    dist\veaja-1.0.0-windows-x64\veaja.exe
```

**Step 3 — Verify the signature**

```cmd
signtool verify /pa /v dist\veaja-1.0.0-windows-x64\veaja.exe
```

### Sign with a real OV certificate (removes SmartScreen warning)

To remove the "Windows protected your PC" SmartScreen warning, you need an
**OV (Organization Validated)** or **EV (Extended Validation)** certificate
from a trusted Certificate Authority.

**Recommended CAs (cheapest to most expensive):**
- [Certum](https://www.certum.eu) — ~$100/yr (OV)
- [Sectigo](https://sectigo.com) — ~$200/yr (OV)
- [DigiCert](https://digicert.com) — ~$500/yr (EV — instant SmartScreen trust)

**Process:**
1. Buy the certificate from a CA
2. They verify your identity (OV: business docs; EV: stricter verification)
3. They issue a `.pfx` file
4. Use the same `signtool sign` command above with your real `.pfx`

> **EV certificates** are stored on a USB hardware token (HSM). SmartScreen trusts
> them immediately without needing reputation buildup.

---

## macOS

### Build

On a Mac with Python and the venv set up:

```bash
source venv/bin/activate
pip install pyinstaller
pyinstaller veaja.spec --clean --noconfirm

# Package as DMG (requires create-dmg)
brew install create-dmg
create-dmg \
    --volname "Veaja" \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "veaja.app" 150 200 \
    --app-drop-link 450 200 \
    "dist/veaja-1.0.0-macos.dmg" \
    "dist/veaja/"
```

### Sign and notarize (required — Gatekeeper blocks unsigned apps)

macOS **Gatekeeper** will block unsigned apps with "cannot be opened because the developer
cannot be verified." You must sign AND notarize to distribute to other Macs.

**Requirements:**
- Apple Developer account: $99/year at [developer.apple.com](https://developer.apple.com)

**Step 1 — Get your Developer ID certificate**

1. Log in to [developer.apple.com](https://developer.apple.com)
2. Go to **Certificates, IDs & Profiles** → **Certificates**
3. Click **+** → choose **Developer ID Application**
4. Follow the CSR (Certificate Signing Request) process
5. Download and double-click the `.cer` file to install in Keychain

**Step 2 — Sign the app**

```bash
# Find your certificate identity
security find-identity -v -p codesigning
# Look for: "Developer ID Application: Your Name (TEAMID)"

# Sign the app bundle
codesign \
    --deep \
    --force \
    --verify \
    --verbose \
    --sign "Developer ID Application: Your Name (XXXXXXXXXX)" \
    --options runtime \
    --entitlements entitlements.plist \
    dist/veaja.app
```

Create `entitlements.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <false/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <false/>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
    <key>com.apple.security.device.audio-input</key>
    <false/>
</dict>
</plist>
```

**Step 3 — Notarize with Apple**

```bash
# Create an app-specific password at appleid.apple.com
# Then store it in keychain:
xcrun notarytool store-credentials "veaja-notary" \
    --apple-id "your@apple.id" \
    --team-id "XXXXXXXXXX" \
    --password "xxxx-xxxx-xxxx-xxxx"

# Submit for notarization
xcrun notarytool submit dist/veaja-1.0.0-macos.dmg \
    --keychain-profile "veaja-notary" \
    --wait

# Staple the notarization ticket to the DMG
xcrun stapler staple dist/veaja-1.0.0-macos.dmg
```

**Step 4 — Verify**

```bash
spctl --assess --verbose dist/veaja.app
# Should say: dist/veaja.app: accepted
```

---

## GitHub Releases — publishing

Once you have your build artifacts:

```bash
# Tag the release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

Then on GitHub:
1. Go to your repo → **Releases** → **Draft a new release**
2. Choose tag `v1.0.0`
3. Upload your artifacts:
   - `veaja-1.0.0-linux-x86_64.tar.gz` + `.asc` + `.sha256`
   - `veaja-1.0.0-windows-x64.zip` (or `.exe` installer)
   - `veaja-1.0.0-macos.dmg`
   - `veaja-public-key.asc`
4. Write release notes
5. Publish

---

## Recommended release checklist

```
[ ] Bump version in config/settings.py
[ ] Update ARCHITECTURE.md and README.md
[ ] Run the app and test all features
[ ] git tag -a v1.0.0 -m "Release v1.0.0"
[ ] Build Linux: ./build_linux.sh
[ ] Sign Linux: gpg --detach-sign ...
[ ] Build Windows (on Windows machine)
[ ] Sign Windows: signtool sign ...
[ ] Build macOS (on Mac)
[ ] Sign + notarize macOS: codesign + notarytool
[ ] Upload all artifacts to GitHub Releases
[ ] Publish release
```

---

## Summary: what signing actually does

| Signing type | What it prevents | Cost |
|---|---|---|
| GPG (Linux) | Tampering with the download | Free |
| Self-signed (Windows) | Nothing (SmartScreen still warns) | Free |
| OV cert (Windows) | SmartScreen warning after reputation builds | ~$100/yr |
| EV cert (Windows) | SmartScreen warning immediately | ~$500/yr |
| Apple Developer ID | Gatekeeper blocking the app | $99/yr |

For a personal/open-source project, **GPG on Linux** is the most practical starting point.
Windows and macOS signing are only necessary when distributing to non-technical users who
would be confused by security warnings.
