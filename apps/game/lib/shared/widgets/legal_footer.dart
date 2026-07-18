import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

/// Links to the static Impressum/Datenschutzerklärung pages served
/// alongside the app by Firebase Hosting (apps/game/web/impressum.html,
/// datenschutz.html — plain static files, copied through unmodified by
/// `flutter build web`, not Flutter routes). Opened via url_launcher
/// rather than an in-app route: these are plain legal documents, not part
/// of the game's own navigation, and keeping them as static HTML means
/// they render and are reachable even if the Flutter app itself fails to
/// boot for some reason.
class LegalFooter extends StatelessWidget {
  const LegalFooter({super.key});

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(
      context,
    ).textTheme.bodySmall?.copyWith(decoration: TextDecoration.underline);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          TextButton(
            onPressed: () => _open('impressum.html'),
            child: Text('Impressum', style: style),
          ),
          Text('·', style: Theme.of(context).textTheme.bodySmall),
          TextButton(
            onPressed: () => _open('datenschutz.html'),
            child: Text('Datenschutz', style: style),
          ),
        ],
      ),
    );
  }

  Future<void> _open(String path) async {
    final uri = Uri.base.resolve(path);
    await launchUrl(uri, webOnlyWindowName: '_blank');
  }
}
