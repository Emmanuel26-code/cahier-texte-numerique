"""Services du module IA : extraction du texte, appel au LLM, création du plan.

Chaîne complète : Document -> texte (extraction) -> JSON (llm) -> arbre validé
(schema) -> Plan + Titres en base (builder). Le point d'entrée est
`generation.generer_plan_pour_document`.
"""
