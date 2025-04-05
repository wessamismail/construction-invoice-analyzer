# Construction Invoice Analyzer

تطبيق تحليل فواتير الإنشاء باستخدام Python و Streamlit

## المميزات
- تحليل فواتير PDF و Excel والصور
- استخراج البنود والكميات والأسعار تلقائياً
- مقارنة مع التسعير المبدئي
- حساب الفروقات وتصنيف المصروفات
- تقارير رسومية تفاعلية
- توليد تقارير PDF
- تنبيهات ذكية
- تقارير أسبوعية
- تكامل مع Xero (قريباً)

## المتطلبات
- Python 3.8+
- Tesseract OCR
- OpenAI API Key (للميزات الذكية)
- Xero API credentials (للتكامل)

## التثبيت
1. قم بتثبيت المتطلبات:
```bash
pip install -r requirements.txt
```

2. قم بتثبيت Tesseract OCR:
- macOS: `brew install tesseract`
- Linux: `sudo apt-get install tesseract-ocr`
- Windows: قم بتحميله من [الموقع الرسمي](https://github.com/UB-Mannheim/tesseract/wiki)

3. أنشئ ملف `.env` وأضف المتغيرات البيئية:
```
OPENAI_API_KEY=your_key_here
XERO_CLIENT_ID=your_client_id
XERO_CLIENT_SECRET=your_client_secret
```

## التشغيل
```bash
streamlit run app.py
```

## هيكل المشروع
```
construction_invoice_analyzer/
├── data/               # مجلد البيانات
├── models/            # نماذج المعالجة
├── utils/             # أدوات مساعدة
├── pages/             # صفحات التطبيق
├── tests/             # اختبارات
├── database/          # قاعدة البيانات
├── app.py             # التطبيق الرئيسي
└── requirements.txt   # المتطلبات
```

## المساهمة
نرحب بمساهماتكم! يرجى إنشاء issue أو pull request.

## الترخيص
MIT License 