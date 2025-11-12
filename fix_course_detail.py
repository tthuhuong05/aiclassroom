#!/usr/bin/env python3
"""
Script để sửa lỗi trong course_detail.html
"""

import re

def fix_course_detail():
    """Sửa lỗi trong course_detail.html"""
    
    # Đọc file hiện tại
    with open('templates/course_detail.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Sửa lỗi phụ đề - đảm bảo track elements đúng
    subtitle_fix = '''
                <track id="trackSubs" kind="subtitles" srclang="en" label="Subtitles" default
                 {% if course.caption_url %}src="{{ course.caption_url }}"{% endif %}>
                <track id="trackHidden" kind="metadata" srclang="en" label="hidden-parser"
                 {% if course.caption_url %}src="{{ course.caption_url }}"{% endif %}>'''
    
    # 2. Sửa quiz logic - đơn giản hóa
    quiz_fix = '''
// QUIZ LOGIC - Đơn giản và ổn định
(function() {
  console.log('🎯 Quiz logic đang được khởi tạo...');
  
  // Đợi video sẵn sàng
  function waitForVideo() {
    const player = document.getElementById('player');
    if (!player) {
      console.log('❌ Video player not found, retrying...');
      setTimeout(waitForVideo, 100);
      return;
    }
    
    console.log('✅ Video player found');
    setupQuiz();
  }
  
  function setupQuiz() {
    const player = document.getElementById('player');
    const askedAt = new Set();
    let wrongAnswerCount = 0;
    
    // Tạo quiz modal
    const quizModalHTML = `
      <div id="quizModal" style="position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;align-items:center;justify-content:center;z-index:1000">
        <div style="background:#fff;max-width:720px;width:92%;border-radius:16px;padding:24px;box-shadow:0 8px 24px rgba(0,0,0,.25)">
          <h3 style="margin:0 0 8px">📝 Câu hỏi kiểm tra</h3>
          <div id="q-text" style="font-size:18px;margin-bottom:16px"></div>
          <div id="q-choices" style="display:grid;gap:10px;margin:14px 0"></div>
          <div id="q-result" style="min-height:22px;color:#333;margin-top:6px;padding:8px;border-radius:8px"></div>
          <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:10px">
            <button id="btn-continue" style="padding:10px 14px;border-radius:10px;border:1px solid #ddd;background:#2196f3;color:white;cursor:pointer;display:none">Tiếp tục học ▶</button>
          </div>
        </div>
      </div>
    `;
    
    // Thêm modal vào DOM
    document.body.insertAdjacentHTML('beforeend', quizModalHTML);
    
    const modal = document.getElementById('quizModal');
    const qText = document.getElementById('q-text');
    const qChoices = document.getElementById('q-choices');
    const qResult = document.getElementById('q-result');
    const btnCont = document.getElementById('btn-continue');
    
    function showModal() {
      console.log('📱 Hiển thị quiz modal');
      modal.style.display = 'flex';
    }
    
    function hideModal() {
      console.log('❌ Ẩn quiz modal');
      modal.style.display = 'none';
    }
    
    function createQuestion() {
      const questions = [
        {
          question: "Trong 50 giây đầu của video, nội dung chính nói về gì?",
          options: [
            "Giới thiệu tổng quan về chủ đề",
            "Kết luận và tóm tắt",
            "Thảo luận chi tiết",
            "Thực hành và bài tập"
          ],
          correct_index: 0,
          explanation: "50 giây đầu thường là phần giới thiệu tổng quan về chủ đề bài học."
        }
      ];
      return questions[0];
    }
    
    function renderQuestion(qa) {
      console.log('📝 Rendering question:', qa.question);
      qText.textContent = qa.question;
      qResult.textContent = "";
      qResult.className = "result";
      btnCont.style.display = "none";
      qChoices.innerHTML = "";
      
      qa.options.forEach((option, idx) => {
        const button = document.createElement('button');
        button.textContent = `(${String.fromCharCode(65 + idx)}) ${option}`;
        button.style.cssText = "padding:12px 14px;border:1px solid #ddd;border-radius:12px;cursor:pointer;text-align:left;background:white;transition:all 0.2s";
        button.addEventListener('click', () => {
          console.log('🖱️ User clicked option:', idx);
          [...qChoices.children].forEach(x => x.disabled = true);
          
          if (idx === qa.correct_index) {
            qResult.textContent = "✅ Chính xác! " + qa.explanation;
            qResult.className = "result correct";
            qResult.style.cssText = "background:#e8f5e8;color:#2e7d32;padding:8px;border-radius:8px;margin-top:6px";
            console.log('✅ User answered correctly');
          } else {
            wrongAnswerCount++;
            const correct = qa.options[qa.correct_index];
            qResult.textContent = `❌ Chưa đúng. Đáp án đúng là (${String.fromCharCode(65 + qa.correct_index)}) ${correct}. ` + qa.explanation;
            qResult.textContent += " Bạn cần xem lại đoạn video từ đầu để hiểu rõ hơn.";
            qResult.className = "result wrong";
            qResult.style.cssText = "background:#ffebee;color:#c62828;padding:8px;border-radius:8px;margin-top:6px";
            console.log('❌ User answered incorrectly');
          }
          btnCont.style.display = "inline-block";
        });
        qChoices.appendChild(button);
      });
    }
    
    function maybeAsk(now) {
      console.log('⏰ Checking time:', now, 'Asked at:', Array.from(askedAt));
      if (now >= 50 && !askedAt.has("50")) {
        console.log('🎯 Time to show quiz!');
        player.pause();
        showModal();
        const qa = createQuestion();
        askedAt.add("50");
        renderQuestion(qa);
      }
    }
    
    btnCont.addEventListener('click', () => {
      console.log('▶️ Continue button clicked');
      hideModal();
      if (wrongAnswerCount > 0) {
        console.log('🔄 Rewinding video to beginning');
        player.currentTime = 0;
        wrongAnswerCount = 0;
      }
      player.play();
    });
    
    player.addEventListener('timeupdate', () => {
      const t = player.currentTime || 0;
      if (t >= 50 && !askedAt.has("50")) {
        console.log('⏰ Video reached 50 seconds, showing quiz');
        maybeAsk(t);
      }
    });
    
    player.addEventListener('seeked', () => {
      const t = player.currentTime || 0;
      console.log('⏩ Video seeked to:', t);
      if (t >= 50 && !askedAt.has("50")) {
        console.log('⏩ Video seeked past 50 seconds, showing quiz');
        maybeAsk(t);
      }
    });
    
    player.addEventListener('loadstart', () => {
      console.log('🔄 Video loadstart, resetting quiz');
      askedAt.clear();
      wrongAnswerCount = 0;
    });
    
    console.log('✅ Quiz logic đã được khởi tạo thành công');
  }
  
  // Khởi tạo khi DOM sẵn sàng
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', waitForVideo);
  } else {
    waitForVideo();
  }
})();'''
    
    # Thay thế quiz logic cũ
    pattern = r'// QUIZ LOGIC.*?});'
    content = re.sub(pattern, quiz_fix, content, flags=re.DOTALL)
    
    # Ghi file đã sửa
    with open('templates/course_detail_fixed.html', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Đã sửa lỗi và tạo file course_detail_fixed.html")
    print("📋 Các lỗi đã sửa:")
    print("   - ✅ Quiz logic đơn giản hóa")
    print("   - ✅ Đảm bảo video player sẵn sàng")
    print("   - ✅ Xử lý DOM loading đúng cách")
    print("   - ✅ Console log chi tiết để debug")

if __name__ == "__main__":
    fix_course_detail()

