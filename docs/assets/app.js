/* 漏れた後の守り方 — app.js
   外部通信は一切しません。保存はこの端末の localStorage のみ。 */
(function () {
  "use strict";

  var STORE_PREFIX = "moreta:";
  function load(key) {
    try { return window.localStorage.getItem(STORE_PREFIX + key); } catch (e) { return null; }
  }
  function save(key, value) {
    try {
      if (value === null) window.localStorage.removeItem(STORE_PREFIX + key);
      else window.localStorage.setItem(STORE_PREFIX + key, value);
    } catch (e) { /* 保存できない環境でも表示は続ける */ }
  }
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ---------- メニュー：外側クリック・Escで閉じる ---------- */
  function initMenu() {
    var menu = $(".menu-mobile");
    if (!menu) return;
    document.addEventListener("click", function (e) {
      if (menu.open && !menu.contains(e.target)) menu.open = false;
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && menu.open) { menu.open = false; menu.querySelector("summary").focus(); }
    });
  }

  /* ---------- チェックリスト（保存と進捗） ---------- */
  function updateProgress(listName) {
    var list = $('[data-checklist="' + listName + '"]');
    var bar = $('[data-progress-for="' + listName + '"]');
    if (!list) return;
    var boxes = $all('input[type="checkbox"]', list);
    var done = boxes.filter(function (b) { return b.checked; }).length;
    boxes.forEach(function (b) {
      var li = b.closest("li");
      if (li) li.classList.toggle("is-done", b.checked);
    });
    if (bar) {
      var t = $("[data-progress-text]", bar);
      if (t) t.textContent = done + " / " + boxes.length + " 完了";
      var fill = $(".bar > span", bar);
      if (fill) fill.style.width = (boxes.length ? (done / boxes.length) * 100 : 0) + "%";
    }
  }
  function bindChecklist(root) {
    $all("input[data-save]", root).forEach(function (box) {
      if (box.dataset.bound) return;
      box.dataset.bound = "1";
      box.checked = load("check:" + box.dataset.save) === "1";
      box.addEventListener("change", function () {
        save("check:" + box.dataset.save, box.checked ? "1" : null);
        var list = box.closest("[data-checklist]");
        if (list) updateProgress(list.dataset.checklist);
      });
    });
    $all("[data-checklist]", root).forEach(function (l) { updateProgress(l.dataset.checklist); });
  }
  function initChecklists() {
    bindChecklist(document);
    $all("[data-reset]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var list = $('[data-checklist="' + btn.dataset.reset + '"]');
        if (!list) return;
        $all("input[data-save]", list).forEach(function (b) { b.checked = false; save("check:" + b.dataset.save, null); });
        updateProgress(btn.dataset.reset);
      });
    });
  }

  /* ---------- 自分専用の対策 ---------- */
  var LABELS = {
    email: "メールアドレス", password: "パスワード", phone: "電話番号", address: "氏名・住所",
    birth: "生年月日", idimg: "本人確認書類の画像や番号", card: "クレジットカード情報", bank: "口座情報",
    history: "購入・配送・利用の履歴", family: "家族の情報", token: "認証トークン・外部サービス連携", files: "保存した写真・文書など", unknown: "わからない",
    elderly: "高齢の家族がいる", landline: "固定電話がある", netbank: "ネットバンキング・証券", qr: "スマホ決済"
  };
  var GROUPS = [
    { key: "now", label: "今日やる", badge: "now", badgeText: "今日" },
    { key: "week", label: "今週中にやる", badge: "week", badgeText: "今週" },
    { key: "ongoing", label: "これから続ける", badge: "ongoing", badgeText: "継続" },
    { key: "opt", label: "必要に応じて", badge: "opt", badgeText: "任意" }
  ];
  var A = {
    "rule-inbound": { p: "now", t: "「届いた連絡からは動かない」と決める",
      why: "漏れた情報を使った詐欺は、名前や使っているサービスを正しく言い当ててきます。見分けるより、連絡の経路で防ぐほうが確実です。",
      steps: ["メールやSMSのリンクは押さず、公式アプリかブックマークから開く", "電話は一度切り、カード裏面や公式サイトの番号にかけ直す", "訪問者にはドアを開けず、会社や役所の代表番号で確かめる"],
      link: ["scams.html#rule", "詳しく"] },
    "email-lock": { p: "now", t: "メールのログイン方法と再設定先を点検する",
      why: "多くのサービスのパスワード再設定がメールに届くため、メールの乗っ取りは被害を広げる原因になります。",
      steps: ["パスワードが短い・推測されやすい・使い回し・漏えいの対象なら、長くランダムで固有のものへ変更する", "対応するパスキーや多要素認証を設定する。新しい方法でログインできることを確認してから古い方法を変更する", "再設定用の電話番号と予備のメールアドレスが今も自分のものか確認する。不審なログインがあれば被害時の手順へ"],
      link: ["accounts.html#order", "優先順位を見る"] },
    "bank-limit": { p: "now", t: "ネットバンキングの振込限度額を下げる",
      why: "銀行振込による被害額を抑えるための設定です。カードの不正利用やなりすまし契約には効きません。",
      steps: ["銀行のアプリやサイトで、1日の振込限度額を普段必要な最小限にする", "ログイン、振込、出金のお知らせをオンにする"],
      link: ["accounts.html#money", "詳しく"] },
    "card-notify": { p: "now", t: "利用中のカードやスマホ決済の通知をオンにする",
      why: "不正利用は、早く気づくほど止めやすくなります。",
      steps: ["カードを使っている場合は、カード会社の公式アプリで利用通知をオンにする", "スマホ決済を使っている場合は、その利用通知もオンにする"] },
    "phish-email": { p: "now", t: "漏えいした会社を名乗るメールやSMSのリンクを開かない",
      why: "漏れたアドレスには、その会社を名乗る偽の「お詫び」「補償」「再登録」の連絡が届きやすくなります。",
      steps: ["お知らせは、公式サイトを自分で開いて確認する", "補償やポイントの受け取りを急がせる連絡は無視する", "会社がメールでパスワードや認証コードを聞くことはない"],
      link: ["scams.html#notice", "典型的な手口"] },
    "alias": { p: "week", t: "サービスごとに別のメールアドレス（エイリアス）を使う",
      why: "宛先の違いは不審な連絡や流出経路を調べる手掛かりになりますが、メールの真偽や流出元を証明するものではありません。漏れたアドレスだけを止めることもできます。",
      steps: ["iCloud＋の「メールを非公開」や Firefox Relay などで作る", "大事なサービスから順に、登録アドレスを変える"],
      link: ["accounts.html#alias", "作り方"] },
    "pw-change": { p: "now", t: "漏れたパスワードと、使い回しを変更する",
      why: "暗号化とハッシュ化は異なる保管方法です。危険度は方式や別管理の鍵、パスワードの強さによるため、『読めない形式』だけで安全とは判断できません。",
      steps: ["対象サービスの公式案内に従って変更する。停止中なら、先に同じ・似たパスワードを使う他のサービスを変更する", "新しいものはサービスごとに独立して生成する。古いものの末尾だけを変える方法は使わない", "偽サイトへ入力した、不審なログインがある場合は、ログイン済み端末と連携・再設定先の確認も行う"],
      link: ["accounts.html#password", "変更する場合と保管方式の説明"] },
    "pwm": { p: "week", t: "パスワード管理を使い、全部を別々にする",
      why: "長さ・予測しにくさ・サービスごとの独立性をそろえ、1つ漏れた情報で他のサービスへログインされるリスクを減らします。",
      steps: ["OSやブラウザーのパスワード管理、または信頼できる専用アプリを使う", "サービスの制限に合わせ、できれば16文字以上のランダムなパスワードを個別に生成する", "管理ツールの鍵と復旧方法も確認する。秘密の質問は、利用できる安全な別方式があればそちらを選ぶ"],
      link: ["accounts.html#password", "詳しく"] },
    "passkey": { p: "week", t: "大事なサービスをパスキーに切り替える",
      why: "パスキー自体は偽サイトで使えず、SMSの認証コードよりフィッシングに強い方式です。ただし、同じアカウントに残るパスワードなど別のログイン方法は狙われ得ます。",
      steps: ["対応サービスの公式設定から作成し、保存先と別の端末でログインできるか確認する", "機種変更や端末紛失時の復旧手段を確かめる。残るパスワードと再設定先も保護する"],
      link: ["accounts.html#passkey", "パスキーとは"] },
    "carrier-lock": { p: "now", t: "携帯電話会社のIDのパスワードと、契約の暗証番号を見直す",
      why: "偽造した身分証で電話番号を乗っ取られると、SMSの認証コードが全部相手に届きます。",
      steps: ["dアカウント、au ID、My SoftBank、楽天IDなどのパスワードを固有にし、2段階認証をオンにする", "契約時の4桁の暗証番号が生年月日などなら変更する"],
      link: ["accounts.html#carrier", "詳しく"] },
    "sms-filter": { p: "now", t: "携帯会社の迷惑SMSフィルタをオンにする",
      why: "漏れた番号には、詐欺のSMSが増えます。受信前に止められるものは止めます。",
      steps: ["ドコモ「危険SMS拒否設定」、au・UQ mobile・povo「迷惑SMSブロック」、ソフトバンク・ワイモバイル・LINEMO「迷惑SMSフィルター」など", "設定後、必要な認証コードのSMSが届くか確かめる"] },
    "sms-2fa": { p: "week", t: "大事なサービスの認証を、SMSからパスキーや認証アプリへ移す",
      why: "SMSを使う認証はSIM乗っ取りの影響を受けます。選べるならフィッシングに強い認証を使い、SMS以外の方法も用意します。SMSでも認証なしより被害を減らす効果があります。",
      steps: ["公式設定でパスキー・セキュリティキー、または認証アプリが使えるか確認する", "新しい認証と復旧手段を使えることを確かめてから、既存のSMS認証を変更する"] },
    "outage": { p: "ongoing", t: "突然「圏外」「SIMなし」になったら、すぐ携帯会社へ",
      why: "SIM乗っ取りの兆候です。その間に銀行や決済が狙われます。",
      steps: ["家族の電話などから携帯会社に連絡し、回線を止めてもらう", "銀行と決済アプリのログイン履歴を確認する"] },
    "visitor": { p: "ongoing", t: "アポなしの訪問者にドアを開けない",
      why: "住所と名前が分かると、業者、役所、警察を名乗る訪問がしやすくなります。名簿は強盗の下見にも悪用され得ます。",
      steps: ["インターホン越しに用件を聞く", "名乗った会社や役所の代表番号に自分で確認する", "在宅中も鍵をかける"],
      link: ["family.html#visit", "詳しく"] },
    "mail-watch": { p: "ongoing", t: "身に覚えのない郵便物とSMSを見張る",
      why: "知らないカード、請求書、督促、契約書類は、なりすまし契約の兆候です。",
      steps: ["見つけたら、書類の番号ではなく、公式サイトで調べた番号に連絡する"] },
    "known-not-proof": { p: "now", t: "「知っている」は本物の証拠ではない、と覚える",
      why: "名前、住所、生年月日、注文の内容は、いまは詐欺師も知っています。",
      steps: ["自分からかけた電話でなければ、生年月日などを聞かれても答えない", "相手が情報を知っていることを、信用する理由にしない"] },
    "no-birth-pin": { p: "now", t: "暗証番号や秘密の質問に生年月日を使っていたら変える",
      why: "生年月日はもう秘密ではありません。",
      steps: ["キャッシュカード、携帯電話の暗証番号、スマホのロックを見直す", "秘密の質問の答えは、ランダムな文字列にしてパスワード管理に保存する"] },
    "credit-declare": { p: "week", t: "信用情報機関への「本人申告」を検討する",
      why: "カードやローンの審査で参考にされます。機関ごとに受付条件が異なり、預金口座開設や携帯契約を止める制度ではありません。",
      steps: ["CICとJICCの公式案内で、名義悪用防止の申告条件を確かめる", "全国銀行個人信用情報センターは通常の取引で画像を提出しただけの場合、原則として受け付けません。漏えい通知を受けた場合の扱いを公式窓口で確認する", "審査で信用情報を照会しない契約には効かず、悪用防止も保証されません"],
      link: ["id.html#todo", "しくみと限界"] },
    "credit-disclose": { p: "ongoing", t: "必要に応じて、信用情報の開示で確認する",
      why: "身に覚えのない申し込みや契約に、早く気づけます。",
      steps: ["身に覚えのない契約や通知があれば、まず該当会社へ連絡する", "開示の手数料と記録の保持期間を各機関で確認し、知らない照会や契約を調べる。継続して開示する頻度は状況に応じて決める"] },
    "fake-police": { p: "now", t: "「警察」を名乗る電話の筋書きを知っておく",
      why: "漏れた免許証の番号や写真を見せて、信用させてきます。",
      steps: ["警察が電話でお金や口座の確認を求めることはない", "LINEやビデオ通話に誘導されたら切る", "不安なら #9110 か、自分で調べた警察署の番号へ"],
      link: ["scams.html#police", "ニセ警察詐欺"] },
    "license-reissue": { p: "opt", t: "流出した本人確認書類の発行元へ相談する",
      why: "免許証・旅券・マイナンバーカードは手続きが異なります。画像や番号の流出だけで一律に再交付を勧めることはできません。",
      steps: ["書類の種類と、現物の紛失なのか画像・番号の流出なのかを伝え、発行元の公式窓口で対応を確認する", "免許証は住所地の運転免許センター等に、流出時の再交付受付と条件を確認する"],
      link: ["id.html#reissue", "判断の材料"] },
    "card-reissue": { p: "now", t: "漏れたカード情報の範囲を確かめ、カード会社へ相談する",
      why: "番号全体・セキュリティコードと、番号の一部だけでは危険度が異なります。一部の流出だけで必ず再発行が必要とは限りません。",
      steps: ["番号全体を偽サイトへ入力した、全体の流出通知や不正利用がある場合は、すぐカードの裏面の番号など公式窓口へ連絡する", "末尾など一部だけなら公式通知と明細を確認し、不審な利用や不明な点をカード会社へ相談する。再発行はカード会社の案内に従う"] },
    "card-statement": { p: "ongoing", t: "カードの明細を毎月確認する",
      why: "少額の見覚えのない請求は、カードが使えるかの「試し打ち」のことがあります。",
      steps: ["少額でも、覚えのない請求はカード会社に連絡する"] },
    "refund-scam": { p: "now", t: "「返金」「補償金の振込先確認」を名乗る連絡を疑う",
      why: "口座の情報が漏れた人は、返金を口実にした詐欺の標的になります。",
      steps: ["暗証番号を尋ねる会社や役所はない", "補償の案内は、公式サイトを自分で開いて確認する"] },
    "bank-notify-detail": { p: "now", t: "入出金と登録情報の変更のお知らせをオンにする",
      why: "住所や連絡先を勝手に変えられたことに、すぐ気づけます。",
      steps: ["銀行と証券のアプリで、お知らせの設定を確認する"] },
    "context-scam": { p: "now", t: "実際の注文や配送に触れる連絡でも、本物とは限らない",
      why: "購入、配送、予約の履歴が漏れると、実際の内容に合わせた偽の連絡が作れます。",
      steps: ["荷物は、注文したお店の履歴か、宅配会社の公式アプリで追跡番号を入れて確かめる", "予約の変更やキャンセルの連絡は、公式アプリで確かめる"],
      link: ["scams.html#delivery", "典型的な手口"] },
    "family-pass": { p: "now", t: "家族で合言葉と「一度切る」ルールを決める",
      why: "家族構成や住所を知った相手からの「息子です」「警察です」は、以前よりずっと本物らしくなります。",
      steps: ["誕生日や住所など、漏れうる情報を使わない合言葉にする", "お金、カード、暗証番号の話が出たら、一度切ってかけ直すと決める"],
      link: ["family.html#password-word", "合言葉の決め方"] },
    "family-card": { p: "week", t: "「わが家のルール」を印刷して家族に渡す",
      why: "電話の最中に思い出せるよう、目に見える場所に貼ります。",
      steps: ["家族を守るページのカードを印刷し、電話のそばに貼る"],
      link: ["family.html", "カードを開く"] },
    "notice-check": { p: "now", t: "使っていたサービスが漏えいしていないか確かめる",
      why: "退会済みでも対象になることがあります。",
      steps: ["主な漏えい事案の一覧で、使っていたサービスを探す", "該当すれば、公式サイトを自分で開いて通知の内容を確かめ、漏れた項目でこのページを選び直す"],
      link: ["breaches.html", "漏えい事案の一覧"] },
    "hibp": { p: "week", t: "Have I Been Pwned でメールアドレスを確かめる",
      why: "世界の既知の漏えいに含まれているか分かります。国内の今回の事案は反映されていないことがあります。",
      steps: ["haveibeenpwned.com にメールアドレスを入れる", "知らないサイトの「漏えいチェック」には個人情報を入れない"],
      link: ["accounts.html#check", "詳しく"] },
    "delete-unused": { p: "week", t: "使っていないサービスを洗い出し、退会と消去請求をする",
      why: "退会後も一部の情報が残る場合があります。保存する目的と期間を確認し、条件に合う情報の利用停止・消去を請求できます。",
      steps: ["本人確認書類を出したサービスから優先する", "消去請求の文面は、退会・削除のページで作れる"],
      link: ["delete.html", "退会・削除の真実"] },
    "scam-app": { p: "week", t: "スマホに詐欺対策アプリを入れる",
      why: "国際電話番号や、犯行に使われた番号からの着信を警告したり止めたりできます。",
      steps: ["警察庁の公式『推奨アプリ』一覧から案内先を開く。検索広告や届いたリンクから入れない", "対応OSと設定、取得する情報を確かめる。警告・遮断の機能は環境によって異なり、全ての詐欺を止めるものではない"],
      link: ["family.html#phone", "電話の設定"] },
    "answering": { p: "now", t: "固定電話をいつも留守番電話にしておく",
      why: "相手と用件を確かめてから出られます。詐欺の電話は録音を嫌がります。",
      steps: ["電話機の留守番電話をオンにし、在宅中もそのままにする"] },
    "intl-call": { p: "week", t: "固定電話の国際電話を無料で止める",
      why: "詐欺電話には国際電話番号がよく使われています。",
      steps: ["国際電話不取扱受付センター 0120-210-364（無料）。ウェブや郵送でも申し込める", "電話会社によっては、発信を止める別の手続きが必要な場合がある"],
      link: ["family.html#phone", "詳しく"] },
    "securities": { p: "now", t: "証券口座のログインと出金に、2段階認証やパスキーを設定する",
      why: "2025年には証券口座の乗っ取りが多発しました。",
      steps: ["パスキーや多要素認証を設定する", "出金先の口座が変わったときのお知らせを確認する"],
      link: ["accounts.html#money", "詳しく"] },
    "qr-lock": { p: "now", t: "スマホ決済（PayPayなど）の設定を見直す",
      why: "決済アプリは、銀行口座からの自動チャージでお金を引き出される入口になります。",
      steps: ["対応するログイン保護と画面ロックを設定する", "利用通知をオンにし、自動チャージを必要な範囲へ見直す"] },
    "session-revoke": { p: "now", t: "ログイン済み端末と外部サービス連携を見直す",
      why: "パスワードを変えても、第三者のログイン状態や連携用トークンがすべて失効するとは限りません。",
      steps: ["公式設定で、心当たりのないログイン済み端末・セッション・連携アプリを解除する", "認証トークンやアクセスキーの流出通知があれば、発行元の手順で無効化・再発行する。新しい認証情報を入力して流出を調べるサイトは使わない", "再設定先、登録された認証方法、メールの転送設定も点検する"],
      link: ["help.html#account-recovery", "乗っ取りが疑われる場合の手順"] },
    "files-review": { p: "now", t: "保存していた写真・文書の内容に応じて対処する",
      why: "画像や文書に、ログイン情報や身分証・非公開の情報が含まれる場合があります。何が保存されていたかによって対応が変わります。",
      steps: ["公式発表と通知で、対象のファイルや公開範囲を確認する", "パスワードやアクセスキーが写っていれば、その発行元で変更・無効化する。身分証の画像が含まれる場合は発行元に相談する", "脅迫や『削除費用』の要求には応じず、記録を残して警察など公式窓口へ相談する"],
      link: ["help.html", "被害時の連絡先"] }
  };
  /* 同じグループ内の並び順（攻撃者の換金ルートへの効き目が大きい順） */
  var ORDER = [
    "notice-check", "rule-inbound", "email-lock", "carrier-lock", "pw-change", "session-revoke", "files-review", "card-reissue", "refund-scam", "fake-police",
    "phish-email", "known-not-proof", "bank-limit", "card-notify", "securities", "qr-lock", "bank-notify-detail",
    "sms-filter", "no-birth-pin", "context-scam", "family-pass", "answering",
    "credit-declare", "passkey", "pwm", "sms-2fa", "alias", "scam-app", "intl-call", "family-card", "hibp", "delete-unused",
    "outage", "mail-watch", "credit-disclose", "card-statement", "visitor",
    "license-reissue"
  ];
  Object.keys(A).forEach(function (k) { if (ORDER.indexOf(k) < 0) ORDER.push(k); });
  var BASE = ["rule-inbound", "email-lock"];
  var MAP = {
    email: ["phish-email", "alias"],
    password: ["pw-change", "pwm", "passkey"],
    token: ["session-revoke"],
    files: ["files-review"],
    phone: ["carrier-lock", "sms-filter", "sms-2fa", "outage"],
    address: ["known-not-proof", "visitor", "mail-watch"],
    birth: ["known-not-proof", "no-birth-pin"],
    idimg: ["carrier-lock", "fake-police", "credit-declare", "credit-disclose", "mail-watch", "outage", "license-reissue"],
    card: ["card-reissue", "card-statement", "card-notify"],
    bank: ["refund-scam", "bank-notify-detail", "bank-limit"],
    history: ["context-scam", "known-not-proof"],
    family: ["family-pass", "family-card"],
    unknown: ["notice-check", "pwm", "passkey", "hibp", "delete-unused"],
    elderly: ["family-pass", "family-card", "scam-app", "visitor"],
    landline: ["answering", "intl-call"],
    netbank: ["passkey", "securities", "bank-limit"],
    qr: ["qr-lock", "card-notify"]
  };

  function buildPlan(selected) {
    var ids = BASE.slice();
    selected.forEach(function (s) { (MAP[s] || []).forEach(function (id) { if (ids.indexOf(id) < 0) ids.push(id); }); });
    ids.sort(function (a, b) { return ORDER.indexOf(a) - ORDER.indexOf(b); });
    var html = "";
    var chosen = selected.map(function (s) { return LABELS[s]; }).filter(Boolean);
    html += '<h2 id="plan-title" tabindex="-1">あなたの対策リスト</h2>';
    html += '<p class="muted">' + (chosen.length ? "選んだ項目：" + esc(chosen.join("、")) : "項目を選んでいないため、全員に共通の対策だけを表示しています。") + "</p>";
    html += '<div class="progress" data-progress-for="plan"><span data-progress-text></span><span class="bar"><span></span></span></div>';
    html += '<div data-checklist="plan">';
    var n = 0;
    GROUPS.forEach(function (g) {
      var items = ids.filter(function (id) { return A[id].p === g.key; });
      if (!items.length) return;
      html += '<div class="plan-group"><span class="badge ' + g.badge + '">' + g.badgeText + "</span><h3>" + g.label + "</h3></div>";
      html += '<ol class="checklist">';
      items.forEach(function (id) {
        var a = A[id]; n += 1;
        var cid = "p-" + id;
        html += "<li>";
        html += '<div class="check-head"><input type="checkbox" id="' + cid + '" data-save="plan:' + id + '"><label for="' + cid + '">' + esc(a.t) + "</label></div>";
        html += "<details open><summary>なぜ・やり方</summary>";
        html += '<p class="why">' + esc(a.why) + "</p><ul>";
        a.steps.forEach(function (s) { html += "<li>" + esc(s) + "</li>"; });
        html += "</ul>";
        if (a.link) html += '<p><a href="' + esc(a.link[0]) + '">' + esc(a.link[1]) + "</a></p>";
        html += "</details></li>";
      });
      html += "</ol>";
    });
    html += "</div>";
    return html;
  }

  function initPlanner() {
    var form = $("#plan-form");
    var out = $("#plan-result");
    if (!form || !out) return;
    var boxes = $all('input[name="items"]', form);

    function selectedValues() { return boxes.filter(function (b) { return b.checked; }).map(function (b) { return b.value; }); }
    function render(scroll) {
      var sel = selectedValues();
      out.innerHTML = buildPlan(sel);
      bindChecklist(out);
      $("#plan-tools").hidden = false;
      $("#plan-share-note").hidden = false;
      var hash = sel.length ? "#items=" + sel.join(",") : "#items=";
      try { history.replaceState(null, "", hash); } catch (e) { location.hash = hash; }
      if (scroll) {
        var t = $("#plan-title");
        if (t) { t.scrollIntoView({ block: "start" }); t.focus({ preventScroll: true }); }
      }
    }
    function fromHash() {
      var m = /items=([a-z,]*)/.exec(location.hash || "");
      if (!m) return false;
      var vals = m[1] ? m[1].split(",") : [];
      boxes.forEach(function (b) { b.checked = vals.indexOf(b.value) >= 0; });
      return true;
    }
    form.addEventListener("submit", function (e) { e.preventDefault(); render(true); });
    form.addEventListener("reset", function () {
      setTimeout(function () {
        out.innerHTML = "";
        $("#plan-tools").hidden = true;
        $("#plan-share-note").hidden = true;
        try { history.replaceState(null, "", location.pathname); } catch (e) { /* noop */ }
      }, 0);
    });
    if (fromHash()) render(false);
    window.addEventListener("hashchange", function () { if (fromHash()) render(true); });
  }

  /* ---------- 漏えい事案の絞り込み ---------- */
  function norm(s) {
    s = String(s || "");
    if (s.normalize) s = s.normalize("NFKC");
    return s.toLowerCase().replace(/\s+/g, "");
  }
  function initBreaches() {
    var list = $("#breach-list");
    if (!list) return;
    var items = $all("#breach-list > li");
    var q = $("#breach-q");
    var category = $("#breach-category");
    var clear = $("#breach-clear");
    var empty = $("#breach-empty");
    var chips = $all(".chip[data-filter]");
    var count = $("#breach-count");
    var filter = "all";
    function apply() {
      var query = norm(q ? q.value : "");
      var shown = 0;
      items.forEach(function (li) {
        var keys = (li.getAttribute("data-keys") || "").split(" ");
        var okFilter = filter === "all" || keys.indexOf(filter) >= 0;
        var okCategory = !category || category.value === "all" || li.getAttribute("data-category") === category.value;
        var text = norm(li.getAttribute("data-search"));
        var okQuery = !query || text.indexOf(query) >= 0;
        li.hidden = !(okFilter && okCategory && okQuery);
        if (!li.hidden) shown += 1;
      });
      if (count) count.textContent = items.length + "件中 " + shown + "件を表示";
      if (empty) empty.hidden = shown !== 0;
    }
    chips.forEach(function (c) {
      c.addEventListener("click", function () {
        filter = c.getAttribute("data-filter");
        chips.forEach(function (x) { x.setAttribute("aria-pressed", x === c ? "true" : "false"); });
        apply();
      });
    });
    if (q) q.addEventListener("input", apply);
    if (category) category.addEventListener("change", apply);
    if (clear) clear.addEventListener("click", function () {
      if (q) q.value = "";
      if (category) category.value = "all";
      filter = "all";
      chips.forEach(function (chip) { chip.setAttribute("aria-pressed", chip.getAttribute("data-filter") === "all" ? "true" : "false"); });
      apply();
    });
    apply();
  }

  /* ---------- 消去請求の文面 ---------- */
  function initErase() {
    var form = $("#erase-form");
    var out = $("#erase-output");
    if (!form || !out) return;
    var error = $("#erase-error");
    var copy = $('[data-copy="#erase-output"]');
    function v(id) { var el = $("#" + id); return el ? el.value.trim() : ""; }
    function c(id) { var el = $("#" + id); return !!(el && el.checked); }
    function fmtDate(iso) {
      var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
      return m ? m[1] + "年" + Number(m[2]) + "月" + Number(m[3]) + "日" : "";
    }
    function today() {
      var d = new Date();
      return d.getFullYear() + "年" + (d.getMonth() + 1) + "月" + d.getDate() + "日";
    }
    function build(status) {
      var company = v("f-company") || "〇〇株式会社";
      var service = v("f-service") || "〇〇";
      var name = v("f-name") || "（氏名）";
      var email = v("f-email") || "（登録メールアドレス）";
      var member = v("f-member");
      var left = status === "former" ? fmtDate(v("f-left")) : "";
      var target = v("f-target");
      var reasons = [];
      var basis = [];
      if (c("f-r-left")) {
        reasons.push((left ? "私は" + left + "に貴社サービスを退会しており" : "私は貴社サービスを退会しており") + "、請求対象のデータを引き続き利用する必要がなくなったと考えています（法第35条第5項「利用する必要がなくなった場合」）。");
        basis.push("利用する必要がなくなった場合");
      }
      if (c("f-r-leak")) {
        reasons.push("貴社から、私の個人データの漏えい又はそのおそれについて通知を受けています。通知された事態が法第26条第1項本文に規定する事態に該当する場合として、対象データの利用停止又は消去を請求します。漏えいの有無・範囲が未確定の場合は、調査結果と私のデータの該当範囲もご説明ください。");
        basis.push("漏えい等の事態が生じた場合");
      }
      if (c("f-r-harm")) {
        reasons.push("次の事情により、私の権利又は正当な利益が害されるおそれがあります（法第35条第5項）：" + v("f-harm"));
      }
      var items = [];
      items.push("私が識別される保有個人データのうち、上記理由に該当する「" + target + "」の利用停止又は消去" + (c("f-c-id") ? "。私が提出した本人確認書類の画像及び番号も対象に含みます" : ""));
      if (c("f-c-copies")) items.push("上記データのバックアップ、分析用の複製、及び業務委託先が保有する複製についても、合理的に可能な範囲で消去すること。困難な場合は、その理由と、代わりに講じる措置（利用停止、アクセス制限、保存期限後の確実な消去など）をご回答ください");
      if (c("f-c-legal")) items.push("法令により保存義務があるため直ちに消去できない情報がある場合は、その項目、根拠となる法令の名称及び条項、並びに保存期限をご回答いただき、保存期限の経過後に遅滞なく消去すること。また、保存期間中は当該法令上の目的以外に利用しないこと");
      items.push("対応の結果を、法第35条第7項に基づき、書面又は電子メールでご通知いただくこと");

      var t = "";
      t += "件名：保有個人データの利用停止及び消去の請求（個人情報保護法第35条第5項）\n\n";
      t += company + "\n個人情報保護ご担当者様\n\n";
      t += "私は、貴社サービス「" + service + "」の" + (status === "former" ? "元利用者" : "利用者") + "です。個人情報の保護に関する法律（以下「法」といいます。）第35条第5項に基づき、私が識別される保有個人データについて、下記のとおり請求します。\n\n";
      t += "記\n\n";
      t += "1．請求者\n";
      t += "　氏名：" + name + "\n";
      t += "　登録メールアドレス：" + email + "\n";
      if (member) t += "　会員番号等：" + member + "\n";
      if (left) t += "　退会日：" + left + "\n";
      t += "\n2．請求の理由\n";
      reasons.forEach(function (r) { t += "　" + r + "\n"; });
      t += "\n3．請求の内容\n";
      items.forEach(function (it, i) { t += "　(" + (i + 1) + ") " + it + "\n"; });
      if (c("f-c-disclose")) {
        t += "\n4．開示の請求\n";
        t += "　あわせて、法第33条第1項に基づき、上記の消去に先立ち、貴社が保有する私の保有個人データの開示（電磁的記録の提供による方法）を請求します。手数料が必要な場合は、事前にその額と支払方法をお知らせください。\n";
      }
      t += "\n" + (c("f-c-disclose") ? "5" : "4") + "．本人確認\n";
      t += "　貴社所定の本人確認の手続きがある場合は、ご案内ください。\n\n";
      t += "以上\n\n";
      t += today() + "\n" + name + "\n";
      return t;
    }
    function showError(message) {
      if (error) { error.textContent = message; error.hidden = false; error.scrollIntoView({ block: "center", behavior: "instant" }); error.focus({ preventScroll: true }); }
      if (copy) copy.disabled = true;
    }
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var invalid = $all("input:invalid", form);
      ["f-company", "f-name", "f-target"].forEach(function (id) {
        var el = $("#" + id);
        if (el && !v(id) && invalid.indexOf(el) < 0) invalid.push(el);
      });
      if (invalid.length) {
        var names = [];
        invalid.forEach(function (el) {
          var label = el.id ? form.querySelector('label[for="' + el.id + '"]') : null;
          if (!label && el.closest("fieldset")) label = el.closest("fieldset").querySelector("legend");
          var name = label ? label.textContent : "入力項目";
          if (names.indexOf(name) < 0) names.push(name);
        });
        showError("入力を確認してください：" + names.join("、") + "。入力せずに使う場合は［個人情報なしでひな形を作る］を押してください。");
        return;
      }
      var status = form.querySelector('input[name="f-status"]:checked');
      if (!status) { showError("利用状況を選んでください。"); return; }
      if (c("f-r-left") && status.value !== "former") { showError("退会済みを選んだ場合だけ、退会後の利用目的に関する理由を選べます。"); return; }
      if (!c("f-r-left") && !c("f-r-leak") && !c("f-r-harm")) { showError("事実に合う請求理由を少なくとも1つ選んでください。"); return; }
      if (c("f-r-harm") && !v("f-harm")) { showError("権利や正当な利益が害されるおそれの具体的な事情を記入してください。"); return; }
      if (status.value === "former" && v("f-left") && new Date(v("f-left") + "T00:00:00") > new Date()) { showError("退会日は今日以前の日付を入力してください。"); return; }
      if (error) { error.hidden = true; error.textContent = ""; }
      out.value = build(status.value);
      if (copy) copy.disabled = false;
      out.focus({ preventScroll: true });
      out.scrollIntoView({ block: "center", behavior: "instant" });
    });
    var template = $("#erase-template");
    if (template) template.addEventListener("click", function () {
      if (error) { error.hidden = true; error.textContent = ""; }
      out.value = "件名：保有個人データの利用停止又は消去の請求\n\n（会社名）\n個人情報保護ご担当者様\n\n私は貴社サービス『（サービス名）』の（利用中／退会済み）の利用者です。個人情報保護法第35条第5項に基づき、次の情報について利用停止又は消去を請求します。\n\n1．対象情報\n（対象の情報を記入してください）\n\n2．請求理由\n（対象情報の利用目的が終了した、漏えい等の対象となった、又は権利・正当な利益が害されるおそれがある等、該当する理由と事実を記入してください）\n\n3．回答のお願い\n対応の結果をご通知ください。全部又は一部の対応ができない場合には、その理由、引き続き保存する情報・目的・期間と、代わりに講じる措置をご説明ください。本人確認の手続きが必要な場合は、貴社所定の方法をご案内ください。\n\n" + today() + "\n（氏名）\n（登録していた連絡先・会員番号等、本人を特定するために必要な情報）\n";
      if (copy) copy.disabled = false;
      out.focus({ preventScroll: true });
      out.scrollIntoView({ block: "center", behavior: "instant" });
    });
    form.addEventListener("input", function () { if (copy) copy.disabled = true; });
    form.addEventListener("change", function () { if (copy) copy.disabled = true; });
    out.addEventListener("input", function () { if (copy) copy.disabled = !out.value.trim(); });
    $all('button[type="submit"], #erase-template', form).forEach(function (btn) { btn.disabled = false; });
    out.value = "利用状況と請求理由を選び、［文面を作る］を押してください。";
  }

  /* ---------- コピー・印刷 ---------- */
  function copyText(text, btn) {
    function done(ok) {
      if (!btn) return;
      var orig = btn.getAttribute("data-label") || btn.textContent;
      btn.setAttribute("data-label", orig);
      btn.textContent = ok ? "コピーしました" : "コピーできませんでした";
      setTimeout(function () { btn.textContent = orig; }, 2000);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(fallback(text)); });
    } else { done(fallback(text)); }
  }
  function fallback(text) {
    var ta = document.createElement("textarea");
    ta.value = text; ta.setAttribute("readonly", ""); ta.className = "copy-buffer";
    document.body.appendChild(ta); ta.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }
  function initActions() {
    $all("[data-copy]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var el = $(btn.getAttribute("data-copy"));
        if (el) copyText(el.value || el.textContent, btn);
      });
    });
    $all("[data-copy-url]").forEach(function (btn) {
      btn.addEventListener("click", function () { copyText(location.href, btn); });
    });
    $all("[data-print]").forEach(function (btn) {
      btn.addEventListener("click", function () { window.print(); });
    });
    $all("[data-print-card]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.body.classList.add("print-card-only");
        window.print();
        setTimeout(function () { document.body.classList.remove("print-card-only"); }, 500);
      });
    });
    var opened = [];
    window.addEventListener("beforeprint", function () {
      opened = $all("main details:not([open])");
      opened.forEach(function (d) { d.open = true; });
    });
    window.addEventListener("afterprint", function () {
      opened.forEach(function (d) { d.open = false; });
      opened = [];
      document.body.classList.remove("print-card-only");
    });
  }

  function init() {
    initMenu();
    initChecklists();
    initPlanner();
    initBreaches();
    initErase();
    initActions();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
