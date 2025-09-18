-- POSTGRESQL (Moodle)
-- Ajuste o prefixo "{"} se o seu for diferente.
WITH limites AS (
  SELECT
    EXTRACT(EPOCH FROM TIMESTAMP '2025-01-01 00:00:00+00')::BIGINT AS ini,
    EXTRACT(EPOCH FROM NOW())::BIGINT AS fim
)
SELECT
  CASE m.name
    WHEN 'assign'   THEN 'Tarefa'
    WHEN 'quiz'     THEN 'Questionário'
    WHEN 'label'    THEN 'Rótulo'
    WHEN 'forum'    THEN 'Fórum'
    WHEN 'resource' THEN 'Arquivo'
    WHEN 'url'      THEN 'URL'
    WHEN 'page'     THEN 'Página'
    WHEN 'book'     THEN 'Livro'
    WHEN 'lesson'   THEN 'Lição'
    WHEN 'glossary' THEN 'Glossário'
    WHEN 'folder'   THEN 'Pasta'
    WHEN 'choice'   THEN 'Escolha'
    WHEN 'feedback' THEN 'Feedback'
    WHEN 'survey'   THEN 'Pesquisa'
    WHEN 'scorm'    THEN 'SCORM'
    WHEN 'workshop' THEN 'Oficina'
    WHEN 'lti'      THEN 'LTI'
    ELSE INITCAP(m.name)  -- fallback no identificador do módulo
  END AS recurso,
  COUNT(cm.id) AS total_instancias
FROM {course_modules} cm
JOIN {course}  c ON c.id = cm.course
JOIN {modules} m ON m.id = cm.module
JOIN limites     l ON TRUE
WHERE c.startdate BETWEEN l.ini AND l.fim
GROUP BY recurso
ORDER BY total_instancias DESC