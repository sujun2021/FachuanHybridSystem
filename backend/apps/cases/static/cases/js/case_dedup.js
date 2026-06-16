(function () {
  'use strict';

  function getCsrfToken() {
    if (window.FachuanCSRF && window.FachuanCSRF.getToken) return window.FachuanCSRF.getToken() || '';
    const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
    if (tokenElement && tokenElement.value) return tokenElement.value;
    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith('csrftoken=')) return cookie.substring('csrftoken='.length);
    }
    return '';
  }

  document.addEventListener('alpine:init', function () {
    Alpine.data('caseDedupApp', function (config) {
      return {
        caseId: config.caseId,
        detailUrl: config.detailUrl || '',
        materialsUrl: config.materialsUrl || '',
        hasBinding: config.hasBinding,
        bindingInfo: config.bindingInfo || {},
        texts: config.texts || {},

        isScanning: false,
        isExecuting: false,
        scanProgress: 0,
        scanStatusText: '',
        scanStatusDesc: '',
        scanResult: null,
        execProgress: 0,
        message: '',
        messageType: 'success',
        messageTimer: null,

        get noBinding() {
          return !this.hasBinding;
        },

        init() {
          // nothing special on init
        },

        showMessage(message, type) {
          if (this.messageTimer) {
            window.clearTimeout(this.messageTimer);
            this.messageTimer = null;
          }
          this.message = message;
          this.messageType = type || 'success';
          this.messageTimer = window.setTimeout(() => {
            this.message = '';
            this.messageTimer = null;
          }, 6000);
        },

        async startScan() {
          if (this.isScanning) return;
          this.isScanning = true;
          this.scanProgress = 0;
          this.scanStatusText = this.texts.scanning || '正在扫描重复文件';
          this.scanStatusDesc = this.texts.scanningDesc || '正在按大小预分组并计算 MD5 哈希值...';
          this.scanResult = null;

          // 模拟进度（实际扫描过程中后端没有进度回调）
          const progressTimer = window.setInterval(() => {
            if (this.scanProgress < 90) {
              this.scanProgress += Math.random() * 10;
              if (this.scanProgress > 90) this.scanProgress = 90;
            }
          }, 500);

          try {
            const resp = await fetch(`/api/v1/cases/${this.caseId}/dedup-scan`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
              },
              body: JSON.stringify({ scan_subfolder: '', action: 'report' }),
            });

            window.clearInterval(progressTimer);

            if (!resp.ok) {
              const data = await resp.json().catch(() => ({}));
              throw new Error(data.message || data.detail || (this.texts.failed || '扫描失败'));
            }

            const data = await resp.json();
            this.scanResult = data;
            this.scanProgress = 100;
            this.scanStatusText = this.texts.completed || '扫描完成';
            this.scanStatusDesc = '';

            const dupCount = data.summary ? data.summary.total_duplicate_files : 0;
            if (dupCount > 0) {
              this.showMessage(`发现 ${dupCount} 个重复文件，可释放 ${data.summary.total_wasted_mb} MB`, 'warn');
            } else {
              this.showMessage(this.texts.noDuplicates || '未发现重复文件', 'success');
            }
          } catch (err) {
            window.clearInterval(progressTimer);
            this.scanProgress = 0;
            this.scanStatusText = this.texts.failed || '扫描失败';
            this.scanStatusDesc = '';
            this.showMessage((err && err.message) || (this.texts.failed || '扫描失败'), 'error');
          } finally {
            this.isScanning = false;
          }
        },

        async executeDedup(action) {
          if (this.isExecuting) return;

          const confirmMsg = action === 'delete'
            ? (this.texts.confirmDelete || '确定要删除所有重复文件（保留每个组中最新的一份）吗？此操作不可撤销！')
            : (this.texts.confirmRecycle || '确定要将所有重复文件移动到回收目录吗？');

          if (!window.confirm(confirmMsg)) return;

          this.isExecuting = true;
          this.execProgress = 0;

          const progressTimer = window.setInterval(() => {
            if (this.execProgress < 90) {
              this.execProgress += Math.random() * 15;
              if (this.execProgress > 90) this.execProgress = 90;
            }
          }, 400);

          try {
            const resp = await fetch(`/api/v1/cases/${this.caseId}/dedup-execute`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
              },
              body: JSON.stringify({ action: action, dry_run: false }),
            });

            window.clearInterval(progressTimer);

            if (!resp.ok) {
              const data = await resp.json().catch(() => ({}));
              throw new Error(data.message || data.detail || '执行失败');
            }

            const data = await resp.json();
            const resultData = data.data || {};

            // 更新结果
            this.scanResult = resultData;
            this.execProgress = 100;

            const actionCount = (resultData.action_results || []).filter(r => r.success).length;
            const failedCount = (resultData.action_results || []).filter(r => !r.success).length;
            const actionName = action === 'delete' ? '删除' : '移至回收目录';
            let msg = `${actionName}完成：成功 ${actionCount} 个`;
            if (failedCount > 0) msg += `，失败 ${failedCount} 个`;
            this.showMessage(msg, failedCount > 0 ? 'error' : 'success');
          } catch (err) {
            window.clearInterval(progressTimer);
            this.showMessage((err && err.message) || '操作失败', 'error');
          } finally {
            this.isExecuting = false;
          }
        },
      };
    });
  });
})();
