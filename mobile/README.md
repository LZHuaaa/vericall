# VeriCall Mobile App

Flutter mobile app for VeriCall Malaysia.

## Setup

### Prerequisites
- Flutter SDK 3.0+
- Android Studio / VS Code with Flutter extension
- Firebase project (for push notifications)

### Install Dependencies
```bash
cd mobile
flutter pub get
```

### Configure Firebase

1. Create Firebase project at https://console.firebase.google.com
2. Add Android app:
   - Package name: `com.vericall.malaysia`
   - Download `google-services.json` → place in `android/app/`
3. Add iOS app:
   - Bundle ID: `com.vericall.malaysia`
   - Download `GoogleService-Info.plist` → place in `ios/Runner/`

### Run the App
```bash
# Android
flutter run -d android

# iOS
flutter run -d ios

# Web (for testing)
flutter run -d chrome
```

## Project Structure

```
mobile/
├── lib/
│   ├── main.dart              # App entry point
│   ├── screens/
│   │   ├── home_screen.dart   # Dashboard
│   │   ├── call_screen.dart   # Call analysis
│   │   ├── decoy_screen.dart  # Uncle Ah Hock 🎭
│   │   ├── alerts_screen.dart # Family alerts
│   │   └── settings_screen.dart
│   ├── services/
│   │   ├── api_service.dart   # Backend API
│   │   └── audio_service.dart # Recording
│   └── widgets/               # Reusable widgets
└── pubspec.yaml               # Dependencies
```

## Features

- 🛡️ **Home**: Protection status dashboard
- 📞 **Call Analysis**: Record and analyze calls
- 🎭 **Uncle Ah Hock**: AI decoy chat interface
- 🔔 **Alerts**: Family protection notifications
- ⚙️ **Settings**: Protection toggles, family network

## Backend Connection

Update the API URL in `lib/services/api_service.dart`:

```dart
// For Android emulator
static const String baseUrl = 'http://10.0.2.2:5000/api';

// For iOS simulator
static const String baseUrl = 'http://localhost:5000/api';

// For production
static const String baseUrl = 'https://your-backend.com/api';
```

## Build for Release

```bash
# Android APK
flutter build apk --release

# Android App Bundle
flutter build appbundle --release

# iOS
flutter build ios --release
```
