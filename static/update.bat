@echo off
echo =========================
echo رفع التحديثات الى GitHub
echo =========================

git add .
git commit -m "تحديث تلقائي"
git push origin main

echo =========================
echo تم الرفع بنجاح ✔
pause