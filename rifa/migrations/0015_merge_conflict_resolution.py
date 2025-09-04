"""Merge migration para resolver conflito gerado por migrações manuais.

Esta migration não altera modelos; apenas unifica dois ramos da árvore de migrations
para permitir `migrate` sem erros de múltiplos leaf nodes.
"""

from django.db import migrations


class Migration(migrations.Migration):

    # Depend only on the existing merge migration. The previous reference to
    # 'zz_0009_add_pix_fields_manual' pointed to a non-existent/renamed file
    # and caused Django's migration graph NodeNotFoundError.
    dependencies = [
        ('rifa', '0014_merge_20250901_1930'),
    ]

    operations = [
    ]
