import 'package:flutter/material.dart';

/// Runs pre-launch setup, then starts the app returned by [appBuilder].
///
/// Later phases hook config loading, error handling and telemetry setup
/// in here, before [runApp] is called.
void bootstrap(Widget Function() appBuilder) {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(appBuilder());
}
