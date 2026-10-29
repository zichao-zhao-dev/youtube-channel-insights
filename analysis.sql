.headers on
.mode column

-- 1. By content type: does the time spent streaming pay off?
WITH ranked AS (
    SELECT content_type, views,
           ROW_NUMBER() OVER (PARTITION BY content_type ORDER BY views) AS rn,
           COUNT(*)     OVER (PARTITION BY content_type)                AS n
    FROM videos
),
medians AS (
    SELECT content_type, AVG(views) AS median_views
    FROM ranked
    WHERE rn IN ((n + 1) / 2, (n + 2) / 2)
    GROUP BY content_type
)
SELECT v.content_type,
       COUNT(*)                                                       AS videos,
       SUM(v.views)                                                   AS total_views,
       ROUND(100.0 * SUM(v.views) / (SELECT SUM(views) FROM videos), 1) AS pct_of_views,
       m.median_views,
       ROUND(SUM(v.duration_sec) / 3600.0, 1)                         AS hours,
       ROUND(SUM(v.views) / (SUM(v.duration_sec) / 3600.0), 1)        AS views_per_hour
FROM videos v
JOIN medians m ON m.content_type = v.content_type
GROUP BY v.content_type
ORDER BY total_views DESC;



.print ''
.print '-- 2. By topic (topics with at least 3 videos)'
WITH ranked AS (
    SELECT topic, views,
           ROW_NUMBER() OVER (PARTITION BY topic ORDER BY views) AS rn,
           COUNT(*)     OVER (PARTITION BY topic)                AS n
    FROM videos
),
medians AS (
    SELECT topic, AVG(views) AS median_views
    FROM ranked
    WHERE rn IN ((n + 1) / 2, (n + 2) / 2)
    GROUP BY topic
)
SELECT v.topic,
       COUNT(*)                                                         AS videos,
       SUM(v.views)                                                     AS total_views,
       ROUND(100.0 * SUM(v.views) / (SELECT SUM(views) FROM videos), 1) AS pct_of_views,
       m.median_views,
       SUM(v.is_live)                                                   AS live_videos
FROM videos v
JOIN medians m ON m.topic = v.topic
GROUP BY v.topic
HAVING COUNT(*) >= 3
ORDER BY total_views DESC;

.print ''
.print '-- 3. Top 5 videos and how much of the channel they carry'
SELECT substr(title, 1, 30)                                             AS title,
       content_type,
       topic,
       views,
       ROUND(100.0 * views / (SELECT SUM(views) FROM videos), 1)        AS pct_of_views,
       ROUND(100.0 * SUM(views) OVER (ORDER BY views DESC)
             / (SELECT SUM(views) FROM videos), 1)                      AS cumulative_pct
FROM videos
ORDER BY views DESC
LIMIT 5;
