import 'package:flutter/material.dart';

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
    return Card(
      color: isSelected ? Theme.of(context).colorScheme.primaryContainer : null,
      child: ListTile(
        onTap: onTap,
        title: Text(suspect.name),
        subtitle: Text('${suspect.role}\n"${suspect.publicStatement}"'),
        isThreeLine: true,
        selected: isSelected,
        trailing: isSelected ? const Icon(Icons.check_circle) : null,
      ),
    );
  }
}
