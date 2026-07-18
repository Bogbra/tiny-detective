import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../domain/suspect.dart';

class SuspectCard extends StatelessWidget {
  const SuspectCard({
    super.key,
    required this.suspect,
    required this.isSelected,
    required this.onTap,
  });

  final Suspect suspect;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    // ListTile's built-in `selected` state recolors title/subtitle to
    // colorScheme.primary, and its subtitle is dimmed by default even when
    // not selected — both bypass the app's fixed font color (AppColors.
    // onBackground) unless overridden explicitly here, rather than left to
    // ListTile's own resolution logic.
    final textStyle = Theme.of(
      context,
    ).textTheme.bodyLarge?.copyWith(color: AppColors.onBackground);

    return Card(
      color: isSelected ? AppColors.selectedSuspect : null,
      child: ListTile(
        onTap: onTap,
        title: Text(suspect.name, style: textStyle),
        subtitle: Text(
          '${suspect.role}\n"${suspect.publicStatement}"',
          style: textStyle,
        ),
        isThreeLine: true,
        selected: isSelected,
        trailing: isSelected
            ? const Icon(Icons.check_circle, color: AppColors.onBackground)
            : null,
      ),
    );
  }
}
