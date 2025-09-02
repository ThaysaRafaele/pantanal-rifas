"""Merge migration para resolver conflito gerado por migrações manuais.

Esta migration não altera modelos; apenas unifica dois ramos da árvore de migrations
para permitir `migrate` sem erros de múltiplos leaf nodes.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rifa', '0014_merge_20250901_1930'),
        ('rifa', 'zz_0009_add_pix_fields_manual'),
    ]

    operations = [
    ]
