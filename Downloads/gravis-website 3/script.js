// DOM要素の取得
document.addEventListener('DOMContentLoaded', function () {
    // ハンバーガーメニューの機能
    const hamburger = document.querySelector('.hamburger');
    const mobileMenu = document.querySelector('.mobile-menu');
    const mobileNavLinks = document.querySelectorAll('.mobile-nav-links a');

    // ハンバーガーメニューの開閉
    if (hamburger && mobileMenu) {
        hamburger.addEventListener('click', () => {
            // navigation.htmlの内容をindex.htmlに読み込んでモーダルとして表示
            loadNavigationModal();
        });

        // モバイルメニューのリンククリック時にメニューを閉じる
        mobileNavLinks.forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                mobileMenu.classList.remove('active');
                document.body.style.overflow = '';
            });
        });

        // ESCキーでメニューを閉じる
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && mobileMenu.classList.contains('active')) {
                hamburger.classList.remove('active');
                mobileMenu.classList.remove('active');
                document.body.style.overflow = '';
            }
        });

        // メニュー外クリックでメニューを閉じる
        mobileMenu.addEventListener('click', (e) => {
            if (e.target === mobileMenu) {
                hamburger.classList.remove('active');
                mobileMenu.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    }

    // ヘッダーのスクロール効果（改良版）
    const header = document.querySelector('.header');
    const aboutSection = document.querySelector('#about');
    const contactForm = document.querySelector('#contact-form');
    
    if (header && (aboutSection || contactForm)) {
        let lastScrollY = 0;
        let isScrollingDown = false;
        let scrollTimeout;

        const updateHeaderVisibility = () => {
            const currentScrollY = window.scrollY;
            const aboutSectionTop = aboutSection ? aboutSection.offsetTop : 0;
            const headerHeight = header.offsetHeight;
            
            // スクロール方向を判定
            const scrollDifference = Math.abs(currentScrollY - lastScrollY);
            
            if (currentScrollY > lastScrollY && currentScrollY > headerHeight && scrollDifference > 5) {
                // 下スクロール：ヘッダーを隠す（スクロール量が5px以上の場合のみ）
                if (!isScrollingDown) {
                    isScrollingDown = true;
                    header.classList.add('header-hidden');
                    header.classList.remove('header-visible');
                }
            } else if (currentScrollY < lastScrollY && scrollDifference > 5) {
                // 上スクロール：ヘッダーを表示（スクロール量が5px以上の場合のみ）
                if (isScrollingDown) {
                    isScrollingDown = false;
                    header.classList.remove('header-hidden');
                    header.classList.add('header-visible');
                }
            }
            
            // contact.htmlでも常にスクロール機能を有効にする
            if (contactForm && !aboutSection) {
                lastScrollY = currentScrollY;
                return;
            }
            
            // ページ最上部にいる場合は常にヘッダーを表示
            if (currentScrollY <= 10) {
                isScrollingDown = false;
                header.classList.remove('header-hidden');
                header.classList.add('header-visible');
            }

            // 背景色の制御
            if (currentScrollY >= aboutSectionTop - headerHeight) {
                // About section以降：黒背景
                header.classList.remove('header-transparent');
                header.classList.add('header-dark');
            } else {
                // Hero section：透明背景
                header.classList.remove('header-dark');
                header.classList.add('header-transparent');
            }

            lastScrollY = currentScrollY;
        };

        // スロットル関数でパフォーマンス向上
        let ticking = false;
        
        const requestHeaderUpdate = () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    updateHeaderVisibility();
                    ticking = false;
                });
                ticking = true;
            }
        };

        // スクロール連動マーキーアニメーション（About）
        const updateTitleMarquee = () => {
            const titleMarquee = document.querySelector('.about-title-marquee');
            if (!titleMarquee) return;

            const aboutCard = document.querySelector('.about-card');
            if (!aboutCard) return;

            const rect = aboutCard.getBoundingClientRect();
            const windowHeight = window.innerHeight;
            
            // aboutセクションが画面内にある時のみ実行
            if (rect.bottom > 0 && rect.top < windowHeight) {
                // スクロール進行度を計算（0から1の値）
                const scrollProgress = Math.max(0, Math.min(1, (windowHeight - rect.top) / (windowHeight + rect.height)));
                
                // -33.33% から 0% まで移動（33.33%の範囲で移動）
                const translateX = -33.33 + (scrollProgress * 33.33);
                
                titleMarquee.style.transform = `translateX(${translateX}%)`;
            }
        };

        // スクロール連動マーキーアニメーション（Services）
        const updateServicesMarquee = () => {
            const servicesMarquee = document.querySelector('.services-title-marquee');
            if (!servicesMarquee) return;

            const servicesSection = document.querySelector('.services');
            if (!servicesSection) return;

            const rect = servicesSection.getBoundingClientRect();
            const windowHeight = window.innerHeight;
            
            // servicesセクションが画面内にある時のみ実行
            if (rect.bottom > 0 && rect.top < windowHeight) {
                // スクロール進行度を計算（0から1の値）
                const scrollProgress = Math.max(0, Math.min(1, (windowHeight - rect.top) / (windowHeight + rect.height)));
                
                // -33.33% から 0% まで移動（33.33%の範囲で移動）
                const translateX = -33.33 + (scrollProgress * 33.33);
                
                servicesMarquee.style.transform = `translateX(${translateX}%)`;
            }
        };

        // スクロール連動ストライプアニメーション
        const updateStripePattern = () => {
            const stripePattern = document.querySelector('.services-stripe-pattern');
            if (!stripePattern) return;

            const servicesSection = document.querySelector('.services');
            if (!servicesSection) return;

            const rect = servicesSection.getBoundingClientRect();
            const windowHeight = window.innerHeight;
            
            // servicesセクションが画面内にある時のみ実行
            if (rect.bottom > 0 && rect.top < windowHeight) {
                // スクロール進行度を計算（0から1の値）
                const scrollProgress = Math.max(0, Math.min(1, (windowHeight - rect.top) / (windowHeight + rect.height)));
                
                // 右から左に流れる（スピードアップ：移動幅を拡大）
                const backgroundPositionX = scrollProgress * -500;
                
                stripePattern.style.backgroundPosition = `${backgroundPositionX}px 0px`;
            }
        };

        // スクロール連動マーキーアニメーション（Works）
        const updateWorksMarquee = () => {
            const worksMarquee = document.querySelector('.works-title-marquee');
            if (!worksMarquee) return;

            const worksSection = document.querySelector('.works');
            if (!worksSection) return;

            const rect = worksSection.getBoundingClientRect();
            const windowHeight = window.innerHeight;
            
            // worksセクションが画面内にある時のみ実行
            if (rect.bottom > 0 && rect.top < windowHeight) {
                // スクロール進行度を計算（0から1の値）
                const scrollProgress = Math.max(0, Math.min(1, (windowHeight - rect.top) / (windowHeight + rect.height)));
                
                // -33.33% から 0% まで移動（33.33%の範囲で移動）
                const translateX = -33.33 + (scrollProgress * 33.33);
                
                worksMarquee.style.transform = `translateX(${translateX}%)`;
            }
        };

        // スクロール連動マーキーアニメーション（Company）
        const updateCompanyMarquee = () => {
            const companyMarquee = document.querySelector('.company-title-marquee');
            if (!companyMarquee) return;

            const companyCard = document.querySelector('.company-card');
            if (!companyCard) return;

            const rect = companyCard.getBoundingClientRect();
            const windowHeight = window.innerHeight;
            
            // companyセクションが画面内にある時のみ実行
            if (rect.bottom > 0 && rect.top < windowHeight) {
                // スクロール進行度を計算（0から1の値）
                const scrollProgress = Math.max(0, Math.min(1, (windowHeight - rect.top) / (windowHeight + rect.height)));
                
                // -33.33% から 0% まで移動（33.33%の範囲で移動）
                const translateX = -33.33 + (scrollProgress * 33.33);
                
                companyMarquee.style.transform = `translateX(${translateX}%)`;
            }
        };

        // スクロール連動チェッカーパターンアニメーション（Company）
        const updateCompanyCheckerPattern = () => {
            const checkerPattern1 = document.querySelector('.company-checker-pattern');
            const checkerPattern2 = document.querySelector('.company-checker-pattern2');
            if (!checkerPattern1 || !checkerPattern2) {
                console.log('Checker patterns not found');
                return;
            }

            // まずcompany-cardを探し、なければcompanyセクション全体を使用
            let targetElement = document.querySelector('.company-card');
            if (!targetElement) {
                targetElement = document.querySelector('.company');
                console.log('Using .company as target element');
            } else {
                console.log('Using .company-card as target element');
            }
            if (!targetElement) {
                console.log('No target element found');
                return;
            }

            const rect = targetElement.getBoundingClientRect();
            const windowHeight = window.innerHeight;
            
            console.log('Target element rect:', rect);
            console.log('Window height:', windowHeight);
            
            // companyセクションが画面内にある時のみ実行
            if (rect.bottom > 0 && rect.top < windowHeight) {
                // スクロール進行度を計算（0から1の値）
                const scrollProgress = Math.max(0, Math.min(1, (windowHeight - rect.top) / (windowHeight + rect.height)));
                
                // 右から左に流れる（Services sectionと同じ仕組み）
                const backgroundPositionX = scrollProgress * -500;
                
                console.log('Scroll progress:', scrollProgress, 'Background position X:', backgroundPositionX);
                console.log('Setting background position for checker patterns');
                
                checkerPattern1.style.backgroundPosition = `${backgroundPositionX}px 0`;
                checkerPattern2.style.backgroundPosition = `${backgroundPositionX + 25}px 0`; // 少しオフセットを加える
            } else {
                console.log('Target element not in viewport');
            }
        };

        // スクロールイベントリスナー
        window.addEventListener('scroll', () => {
            requestHeaderUpdate();
            updateTitleMarquee();
            updateServicesMarquee();
            updateStripePattern();
            updateWorksMarquee();
            updateCompanyMarquee();
            updateCompanyCheckerPattern();
            
            // スクロールが止まったときの処理
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                // スクロールが止まって少し時間が経ったらヘッダーを表示
                if (isScrollingDown) {
                    header.classList.remove('header-hidden');
                    header.classList.add('header-visible');
                    isScrollingDown = false;
                }
            }, 300); // 300ms後にヘッダーを表示
        });

        // 初期状態の設定
        updateHeaderVisibility();
        updateTitleMarquee();
        updateServicesMarquee();
        updateStripePattern();
        updateWorksMarquee();
        updateCompanyMarquee();
        updateCompanyCheckerPattern();
    }
    // スクロールアニメーションの設定
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    // Intersection Observer for fade-in animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);

    // 要素にfade-inクラスを追加してアニメーション対象にする
    const animateElements = document.querySelectorAll('.about, .services, .works, .company, .work-item, .service-image');
    animateElements.forEach(el => {
        el.classList.add('fade-in');
        observer.observe(el);
    });



    // スムーズスクロール（ナビゲーションリンク用）
    const smoothScrollLinks = document.querySelectorAll('a[href^="#"]');
    smoothScrollLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Work itemsにホバーエフェクト
    const workItems = document.querySelectorAll('.work-item');
    workItems.forEach(item => {
        item.addEventListener('mouseenter', () => {
            item.style.transform = 'translateY(-15px) scale(1.02)';
        });

        item.addEventListener('mouseleave', () => {
            item.style.transform = 'translateY(0) scale(1)';
        });
    });

    // デバイスモックアップのアニメーション
    const deviceMockups = document.querySelectorAll('.device-mockup');
    deviceMockups.forEach(device => {
        // マウスムーブメントに応じた3D効果
        device.addEventListener('mousemove', (e) => {
            const rect = device.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const rotateX = (y - centerY) / centerY * 10;
            const rotateY = (centerX - x) / centerX * 10;

            device.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });

        device.addEventListener('mouseleave', () => {
            device.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg)';
        });
    });

    // ページロード時のアニメーション
    const heroText = document.querySelector('.hero-text h1');

    if (heroText) {
        setTimeout(() => {
            heroText.style.opacity = '1';
            heroText.style.transform = 'translateY(0)';
        }, 500);

        // 初期状態の設定
        heroText.style.opacity = '0';
        heroText.style.transform = 'translateY(30px)';
        heroText.style.transition = 'opacity 1s ease, transform 1s ease';
    }

    // スクロール進行度インジケーター
    const createScrollIndicator = () => {
        const indicator = document.createElement('div');
        indicator.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 4px;
            background: linear-gradient(90deg, #ff0000, #ff6b6b);
            z-index: 9999;
            transition: width 0.3s ease;
        `;
        document.body.appendChild(indicator);

        window.addEventListener('scroll', () => {
            const scrollProgress = (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
            indicator.style.width = scrollProgress + '%';
        });
    };

    createScrollIndicator();

    // サービス画像のホバーエフェクト
    const serviceImages = document.querySelectorAll('.image-placeholder');
    serviceImages.forEach(image => {
        image.addEventListener('mouseenter', () => {
            image.style.transform = 'scale(1.05)';
            image.style.filter = 'brightness(1.1)';
        });

        image.addEventListener('mouseleave', () => {
            image.style.transform = 'scale(1)';
            image.style.filter = 'brightness(1)';
        });

        // 初期トランジション設定
        image.style.transition = 'transform 0.3s ease, filter 0.3s ease';
    });

    // カウンターアニメーション（数値がある場合に使用）
    const animateCounter = (element, start, end, duration) => {
        const startTime = performance.now();
        const update = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = Math.floor(start + (end - start) * progress);
            element.textContent = current;

            if (progress < 1) {
                requestAnimationFrame(update);
            }
        };
        requestAnimationFrame(update);
    };



    // パフォーマンス最適化: 画像の遅延読み込み
    const lazyLoadImages = () => {
        const images = document.querySelectorAll('img[data-src]');

        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    };

    lazyLoadImages();

    // キーボードナビゲーション対応
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            document.body.classList.add('keyboard-navigation');
        }
    });

    document.addEventListener('mousedown', () => {
        document.body.classList.remove('keyboard-navigation');
    });

    // Hero video loading
    const heroVideo = document.querySelector('.hero-video');
    if (heroVideo) {
        // Force video load
        heroVideo.load();
        
        // Handle video errors
        heroVideo.addEventListener('error', function(e) {
            console.warn('Video failed to load:', e);
            // Show fallback background
            heroVideo.style.display = 'none';
        });
        
        // Handle successful load
        heroVideo.addEventListener('loadeddata', function() {
            console.log('Hero video loaded successfully');
        });
        
        // Attempt to play
        heroVideo.play().catch(function(error) {
            console.warn('Video autoplay failed:', error);
        });
    }
    
    // Contact form confirm modal
    const contactFormEl = document.querySelector('.contact-form');
    const confirmOverlay = document.getElementById('contact-confirm-overlay');
    let isConfirmedSubmit = false;
    
    const openConfirmModal = () => {
        if (!contactFormEl || !confirmOverlay) return;
        // Fill confirmation values
        const getValue = (selector) => (contactFormEl.querySelector(selector)?.value || '').trim();
        const getChecked = (selector) => (contactFormEl.querySelector(selector)?.checked ? '同意済み' : '未同意');
        
        document.getElementById('confirm-lastname').textContent = getValue('#lastname');
        document.getElementById('confirm-firstname').textContent = getValue('#firstname');
        document.getElementById('confirm-lastname-kana').textContent = getValue('#lastname-kana');
        document.getElementById('confirm-firstname-kana').textContent = getValue('#firstname-kana');
        document.getElementById('confirm-company').textContent = getValue('#company');
        document.getElementById('confirm-email').textContent = getValue('#email');
        document.getElementById('confirm-phone').textContent = getValue('#phone');
        document.getElementById('confirm-message').textContent = getValue('#message');
        document.getElementById('confirm-privacy').textContent = getChecked('#privacy');
        
        // Show modal
        confirmOverlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    };
    
    if (contactFormEl && confirmOverlay) {
        // Submit via Enter key still opens confirm
        contactFormEl.addEventListener('submit', (e) => {
            if (!isConfirmedSubmit) {
                e.preventDefault();
                openConfirmModal();
            }
        });
        
        // Click on the confirm button (type=button) opens modal
        const confirmButton = document.querySelector('.submit-button');
        if (confirmButton) {
            confirmButton.addEventListener('click', (e) => {
                e.preventDefault();
                openConfirmModal();
            });
        }
        
        const closeConfirm = () => {
            confirmOverlay.style.display = 'none';
            document.body.style.overflow = '';
        };
        
        const editBtn = document.getElementById('confirm-edit');
        const submitBtn = document.getElementById('confirm-submit');
        
        if (editBtn) {
            editBtn.addEventListener('click', closeConfirm);
        }
        
        if (submitBtn) {
            submitBtn.addEventListener('click', () => {
                isConfirmedSubmit = true;
                closeConfirm();
                contactFormEl.requestSubmit();
            });
        }
        
        // Click outside to close
        confirmOverlay.addEventListener('click', (e) => {
            if (e.target === confirmOverlay) closeConfirm();
        });
        
        // Esc to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && confirmOverlay.style.display !== 'none') {
                closeConfirm();
            }
        });
    }
    
    // Navigation Modal の読み込みと表示関数
    function loadNavigationModal() {
        // 既にモーダルが存在する場合は削除
        const existingModal = document.querySelector('.navigation-modal');
        if (existingModal) {
            existingModal.remove();
            return;
        }

        // navigation.htmlの内容を取得
        fetch('navigation.html')
            .then(response => response.text())
            .then(html => {
                // HTMLをパースしてbodyの内容を取得
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const navigationContent = doc.querySelector('.navigation-page');

                if (navigationContent) {
                    // モーダル用のコンテナを作成
                    const modal = document.createElement('div');
                    modal.className = 'navigation-modal';
                    modal.style.cssText = `
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100vw;
                        height: 100vh;
                        z-index: 9999;
                        background: transparent;
                        pointer-events: auto;
                    `;

                    // navigation.htmlの内容をモーダルに追加
                    modal.innerHTML = navigationContent.innerHTML;
                    
                    // navigation.cssのスタイルを適用
                    const link = document.createElement('link');
                    link.rel = 'stylesheet';
                    link.href = 'navigation.css';
                    modal.appendChild(link);

                    // 閉じるボタンのイベントを追加
                    const closeButton = modal.querySelector('.x-button');
                    if (closeButton) {
                        closeButton.addEventListener('click', () => {
                            modal.remove();
                        });
                    }

                    // ESCキーで閉じる
                    const handleEsc = (e) => {
                        if (e.key === 'Escape') {
                            modal.remove();
                            document.removeEventListener('keydown', handleEsc);
                        }
                    };
                    document.addEventListener('keydown', handleEsc);

                    // モーダル外クリックで閉じる
                    modal.addEventListener('click', (e) => {
                        if (e.target === modal) {
                            modal.remove();
                            document.removeEventListener('keydown', handleEsc);
                        }
                    });

                    // モーダルをbodyに追加
                    document.body.appendChild(modal);
                    document.body.style.overflow = 'hidden';

                    // モーダル内リンククリックでモーダルを閉じる
                    const modalLinks = modal.querySelectorAll('a');
                    if (modalLinks && modalLinks.length > 0) {
                        modalLinks.forEach(link => {
                            link.addEventListener('click', () => {
                                // 閉じてスクロール制御を解除（遷移はブラウザに任せる）
                                modal.remove();
                                document.removeEventListener('keydown', handleEsc);
                                document.body.style.overflow = '';
                            });
                        });
                    }
                }
            })
            .catch(error => {
                console.error('Navigation modal load error:', error);
            });
    }

    // 言語切り替え機能
    const langButtons = document.querySelectorAll('.lang-btn');
    const jpContent = document.querySelector('.jp-content');
    const engContent = document.querySelector('.eng-content');

    if (langButtons.length > 0) {
        langButtons.forEach(button => {
            button.addEventListener('click', () => {
                const lang = button.getAttribute('data-lang');
                
                // アクティブクラスを切り替え
                langButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                
                // コンテンツを切り替え
                if (lang === 'jp') {
                    jpContent.classList.add('active');
                    engContent.classList.remove('active');
                } else if (lang === 'eng') {
                    jpContent.classList.remove('active');
                    engContent.classList.add('active');
                }
            });
        });
    }

    console.log('Gravis website loaded successfully! 🎉');
}); 