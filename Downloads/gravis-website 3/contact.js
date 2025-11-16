// ============================================
// Google Apps ScriptのウェブアプリURL
// ============================================
const GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbwXdX2I49JHWgXKB0b2DdS28gg_V3mrWZR1zxQa1ZrF_WWQF7Ot6YfGNm-qMC_0lP9T/exec';

document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.contact-form');
    const confirmButton = document.querySelector('.submit-button');
    const confirmOverlay = document.getElementById('contact-confirm-overlay');
    const confirmEditButton = document.getElementById('confirm-edit');
    const confirmSubmitButton = document.getElementById('confirm-submit');

    // 確認ボタンクリック時
    if (confirmButton) {
        confirmButton.addEventListener('click', function() {
            if (form.checkValidity()) {
                showConfirmModal();
            } else {
                form.reportValidity();
            }
        });
    }

    // 確認モーダルを表示
    function showConfirmModal() {
        const formData = {
            lastname: document.getElementById('lastname').value,
            firstname: document.getElementById('firstname').value,
            lastnameKana: document.getElementById('lastname-kana').value,
            firstnameKana: document.getElementById('firstname-kana').value,
            company: document.getElementById('company').value,
            email: document.getElementById('email').value,
            phone: document.getElementById('phone').value,
            message: document.getElementById('message').value,
            privacy: document.getElementById('privacy').checked
        };

        // 確認画面に表示
        document.getElementById('confirm-lastname').textContent = formData.lastname;
        document.getElementById('confirm-firstname').textContent = formData.firstname;
        document.getElementById('confirm-lastname-kana').textContent = formData.lastnameKana;
        document.getElementById('confirm-firstname-kana').textContent = formData.firstnameKana;
        document.getElementById('confirm-company').textContent = formData.company || '（未記入）';
        document.getElementById('confirm-email').textContent = formData.email;
        document.getElementById('confirm-phone').textContent = formData.phone;
        document.getElementById('confirm-message').textContent = formData.message;
        document.getElementById('confirm-privacy').textContent = formData.privacy ? '同意する' : '同意しない';

        confirmOverlay.style.display = 'flex';
    }

    // 修正ボタン
    if (confirmEditButton) {
        confirmEditButton.addEventListener('click', function() {
            confirmOverlay.style.display = 'none';
        });
    }

    // 送信ボタン
    if (confirmSubmitButton) {
        confirmSubmitButton.addEventListener('click', async function() {
            await submitFormToGoogleSheets();
        });
    }

    // Googleスプレッドシートに送信
    async function submitFormToGoogleSheets() {
        // ボタンを無効化
        confirmSubmitButton.disabled = true;
        confirmSubmitButton.innerHTML = '<span>送信中...</span>';

        const formData = {
            lastname: document.getElementById('lastname').value,
            firstname: document.getElementById('firstname').value,
            lastnameKana: document.getElementById('lastname-kana').value,
            firstnameKana: document.getElementById('firstname-kana').value,
            company: document.getElementById('company').value,
            email: document.getElementById('email').value,
            phone: document.getElementById('phone').value,
            message: document.getElementById('message').value
        };

        try {
            const response = await fetch(GOOGLE_SCRIPT_URL, {
                method: 'POST',
                mode: 'no-cors',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            // no-corsモードでは詳細なレスポンスを取得できないため、成功とみなす
            showSuccessMessage();

        } catch (error) {
            console.error('Error:', error);
            showErrorMessage();
        }
    }

    // 成功メッセージ
    function showSuccessMessage() {
        confirmOverlay.style.display = 'none';

        // フォームをリセット
        form.reset();

        // 成功メッセージを表示
        const successModal = document.createElement('div');
        successModal.className = 'success-modal-overlay';
        successModal.innerHTML = `
            <div class="success-modal">
                <h2>送信完了</h2>
                <p>お問い合わせいただきありがとうございます。<br>
                内容を確認の上、担当者より折り返しご連絡させていただきます。</p>
                <button class="success-close">閉じる</button>
            </div>
        `;
        document.body.appendChild(successModal);

        // 閉じるボタン
        successModal.querySelector('.success-close').addEventListener('click', function() {
            document.body.removeChild(successModal);
        });

        // ボタンを有効化
        confirmSubmitButton.disabled = false;
        confirmSubmitButton.innerHTML = '<span>この内容で送信</span>';
    }

    // エラーメッセージ
    function showErrorMessage() {
        alert('送信中にエラーが発生しました。もう一度お試しください。');

        // ボタンを有効化
        confirmSubmitButton.disabled = false;
        confirmSubmitButton.innerHTML = '<span>この内容で送信</span>';
    }

    // オーバーレイクリックで閉じる
    if (confirmOverlay) {
        confirmOverlay.addEventListener('click', function(e) {
            if (e.target === confirmOverlay) {
                confirmOverlay.style.display = 'none';
            }
        });
    }
});
