const { post } = require('../../utils/request');
const upload = require('../../utils/upload');
const options = require('../../utils/options');

Page({
  data: {
    mode: 'text',
    title: '',
    subject: '',
    examBatch: '',
    paperText: '',
    paperTextLength: 0,
    imagePath: '',
    imageName: '',
    uploadProgress: 0,
    ocrPreview: null,
    ocrText: '',
    ocrTextLength: 0,
    ocrStage: '',
    optionMap: {},
    loading: false,
    paperResult: null,
    keyPointNames: [],
    difficultySection: [],

    combinedStudentId: '',
    combinedLoading: false,
    combinedResult: null,

    errorMsg: '',
  },

  onLoad() {
    this.loadOptions();
  },

  loadOptions() {
    options.loadOptionMap(['paper_titles', 'subjects', 'exam_batches'])
      .then((optionMap) => {
        this.setData({ optionMap });
      });
  },

  onTitleInput(e) {
    this.setData({ title: e.detail.value, errorMsg: '' });
  },

  onSubjectInput(e) {
    this.setData({ subject: e.detail.value, errorMsg: '' });
  },

  onBatchInput(e) {
    this.setData({ examBatch: e.detail.value });
  },

  onPaperTextInput(e) {
    this.setData({
      paperText: e.detail.value,
      paperTextLength: e.detail.value.length,
      errorMsg: '',
    });
  },

  onCombinedStudentIdInput(e) {
    this.setData({ combinedStudentId: e.detail.value });
  },

  onPickOption(e) {
    const { type, field } = e.currentTarget.dataset;
    const index = Number(e.detail.value);
    const list = this.data.optionMap[type] || [];
    if (!list.length) {
      wx.showToast({ title: '暂无可选项，可手动输入', icon: 'none' });
      return;
    }
    const item = list[index];
    if (item) {
      this.setData({ [field]: item.value, errorMsg: '' });
    }
  },

  onPickerTap(e) {
    const type = e.currentTarget.dataset.type;
    const list = this.data.optionMap[type] || [];
    const status = options.getOptionStatus(type);
    if (status.loading) {
      wx.showToast({ title: '正在加载选项，请稍候', icon: 'none' });
      return;
    }
    if (status.error && !list.length) {
      wx.showToast({ title: '选项加载失败，可手动输入', icon: 'none' });
      return;
    }
    if (!list.length) {
      wx.showToast({ title: '暂无可选项，可手动输入', icon: 'none' });
    }
  },

  onModeChange(e) {
    this.setData({
      mode: e.currentTarget.dataset.mode,
      paperResult: null,
      combinedResult: null,
      errorMsg: '',
    });
  },

  onChooseImage() {
    const chooseSuccess = (path, name) => {
      this.setData({
        imagePath: path,
        imageName: name || '试卷图片',
        uploadProgress: 0,
        ocrPreview: null,
        ocrText: '',
        ocrTextLength: 0,
        ocrStage: '',
        paperResult: null,
        combinedResult: null,
        errorMsg: '',
      });
    };

    if (wx.chooseMedia) {
      wx.chooseMedia({
        count: 1,
        mediaType: ['image'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          const file = (res.tempFiles || [])[0];
          if (file) {
            chooseSuccess(file.tempFilePath, file.tempFilePath.split('/').pop());
          }
        },
      });
      return;
    }

    wx.chooseImage({
      count: 1,
      sourceType: ['album', 'camera'],
      success: (res) => {
        const path = (res.tempFilePaths || [])[0];
        if (path) {
          chooseSuccess(path, path.split('/').pop());
        }
      },
    });
  },

  onAnalyze() {
    const { title, subject, paperText } = this.data;

    if (!title.trim()) {
      this.setData({ errorMsg: '请输入试卷标题' });
      return;
    }
    if (!subject.trim()) {
      this.setData({ errorMsg: '请输入学科' });
      return;
    }
    if (!paperText.trim()) {
      this.setData({ errorMsg: '请粘贴试卷文本' });
      return;
    }

    this.setData({ loading: true, paperResult: null, combinedResult: null, errorMsg: '' });

    post('/api/ai/exam-paper/analyze', {
      title: title.trim(),
      subject: subject.trim(),
      exam_batch: this.data.examBatch || undefined,
      paper_text: paperText.trim(),
    })
      .then((data) => {
        this.applyPaperResult(data);
        wx.showToast({ title: '分析完成', icon: 'success' });
      })
      .catch((err) => {
        this.setData({ errorMsg: err.message || '分析失败，请重试' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onAnalyzeImage() {
    const { title, subject, examBatch, imagePath } = this.data;

    if (!title.trim()) {
      this.setData({ errorMsg: '请输入试卷标题' });
      return;
    }
    if (!subject.trim()) {
      this.setData({ errorMsg: '请输入学科' });
      return;
    }
    if (!examBatch.trim()) {
      this.setData({ errorMsg: '请输入考试批次' });
      return;
    }
    if (!imagePath) {
      this.setData({ errorMsg: '请选择试卷图片' });
      return;
    }

    this.setData({
      loading: true,
      paperResult: null,
      combinedResult: null,
      errorMsg: '',
      uploadProgress: 0,
      ocrStage: 'uploading',
    });
    const task = upload.uploadFile({
      filePath: imagePath,
      fileName: this.data.imageName,
      fieldName: 'image',
      localPath: '/api/ai/exam-paper/ocr-preview',
      cloudPath: '/api/uploads/cloud/exam-paper/ocr-preview',
      cloudKind: 'exam-images',
      onProgress: (progress) => this.setData({ uploadProgress: progress }),
      timeout: 90000,
    });
    task.promise
      .then((data) => {
        const text = data.normalized_text || data.raw_text || '';
        this.setData({
          ocrPreview: data,
          ocrText: text,
          ocrTextLength: text.length,
          ocrStage: 'preview',
        });
        wx.showToast({ title: 'OCR 预览已生成', icon: 'success' });
      })
      .catch((err) => {
        this.setData({ errorMsg: err.message || '图片上传或 OCR 失败', ocrStage: 'failed' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onOcrTextInput(e) {
    const value = e.detail.value || '';
    this.setData({ ocrText: value, ocrTextLength: value.length, errorMsg: '' });
  },

  onConfirmOcr() {
    const { ocrPreview, ocrText, title, subject, examBatch } = this.data;
    if (!ocrPreview || !ocrPreview.ocr_id) {
      this.setData({ errorMsg: '请先上传图片并完成 OCR 预览' });
      return;
    }
    if (!ocrText.trim()) {
      this.setData({ errorMsg: '请检查并补充识别文字后再确认分析' });
      return;
    }
    this.setData({ loading: true, ocrStage: 'analyzing', errorMsg: '' });
    post('/api/ai/exam-paper/analyze-ocr', {
      ocr_id: ocrPreview.ocr_id,
      title: title.trim(),
      subject: subject.trim(),
      exam_batch: examBatch.trim(),
      corrected_text: ocrText.trim(),
    })
      .then((data) => {
        this.applyPaperResult(data);
        this.setData({ ocrStage: 'done' });
        wx.showToast({ title: '分析完成', icon: 'success' });
      })
      .catch((err) => {
        this.setData({ errorMsg: err.message || 'OCR 文字分析失败', ocrStage: 'failed' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  applyPaperResult(data) {
    const keyPointNames = (data.key_points || []).map((kp) => {
      if (typeof kp === 'string') return kp;
      return `${kp.name}（${kp.relevance || '中频'}）`;
    });

    const difficultySection = [{
      title: data.difficulty || '中等',
      content: data.difficulty_reason || '',
    }];

    this.setData({
      paperResult: data,
      keyPointNames: keyPointNames,
      difficultySection: difficultySection,
    });
  },

  onCombinedAdvice() {
    const { combinedStudentId, paperResult } = this.data;

    if (!combinedStudentId.trim()) {
      this.setData({ errorMsg: '请输入学号' });
      return;
    }
    if (!paperResult || !paperResult.paper_id) {
      this.setData({ errorMsg: '请先分析试卷' });
      return;
    }

    this.setData({ combinedLoading: true, combinedResult: null, errorMsg: '' });

    post('/api/ai/combined-advice', {
      student_id: combinedStudentId.trim(),
      paper_id: paperResult.paper_id,
      term: undefined,
    })
      .then((data) => {
        this.setData({ combinedResult: data });
        wx.showToast({ title: '建议生成完成', icon: 'success' });
      })
      .catch((err) => {
        this.setData({ errorMsg: err.message || '生成失败，请重试' });
      })
      .finally(() => {
        this.setData({ combinedLoading: false });
      });
  },
});
