"""Plan IA services — D-17 ciclo de cierre post-ejecución.

Contains:
- seguimiento_service: daily tracking of recommendations in 14d window (T8)
- cierre_service: auto-close recommendations when window ends (T9)
- memoria_service: aggregates completed recommendations for block #10.7 (T10)
- reporte_semanal: weekly PDF report generator (T11)
"""
