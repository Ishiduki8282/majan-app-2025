# app.py

from flask import Flask, render_template, request, redirect, url_for, session
import json # データをJSON形式で扱うために必要
import os
app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # セッション管理に必要な秘密鍵。本番ではもっと複雑に！

# 仮のデータベースとして、メモリ上にスコア記録を保持
# 実際にはファイルやデータベースに保存しますが、今回はシンプルにします
# 例: {'2023-10-27': [{'player1': 25.0, 'player2': -5.0, 'player3': 15.0, 'player4': -35.0, 'rank': {'player1': 1, ...}}]}
game_records = {}

# --- アプリのルート（一番最初のアクセス先） ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # POSTリクエスト（フォーム送信）があった場合、スコア計算処理を実行

        # プレイヤー名を取得
        player_names = [request.form[f'player{i}_name'] for i in range(1, 5)]

        # 和了点を取得し、int型に変換
        # 和了点がない場合は0とする
        points = []
        for i in range(1, 5):
            try:
                points.append(int(request.form[f'player{i}_points']))
            except ValueError: # 数字ではない場合など
                points.append(0)

        # ウマ・オカ・レートの設定を取得
        uma_1 = int(request.form.get('uma_1', 20)) # デフォルト値 20
        uma_2 = int(request.form.get('uma_2', 10)) # デフォルト値 10
        uma_3 = int(request.form.get('uma_3', -10)) # デフォルト値 -10
        uma_4 = int(request.form.get('uma_4', -20)) # デフォルト値 -20
        oka = int(request.form.get('oka', 25)) # デフォルト値 25
        rate = float(request.form.get('rate', 1.0)) # デフォルト値 1.0 (1.0 = 1000点あたり1円)

        uma_settings = {1: uma_1, 2: uma_2, 3: uma_3, 4: uma_4}

        # スコア計算
        results = calculate_mahjong_score(player_names, points, uma_settings, oka, rate)

        # セッションに結果を保存して、ページ遷移後も表示できるようにする
        session['last_results'] = results
        session['last_settings'] = {
            'uma_1': uma_1, 'uma_2': uma_2, 'uma_3': uma_3, 'uma_4': uma_4,
            'oka': oka, 'rate': rate
        }

        # 計算結果を表示するためにページをリロード（GETリクエストに変換）
        return redirect(url_for('index'))

    # GETリクエスト（初期表示またはリロード）の場合

    # 前回計算した結果があれば取得
    results = session.pop('last_results', None) # 1回表示したらセッションから削除
    settings = session.pop('last_settings', None) # 1回表示したらセッションから削除

    # テンプレートをレンダリングしてブラウザに表示
    return render_template('index.html', results=results, settings=settings, records=game_records)

# --- スコア記録の保存ルート ---
@app.route('/save_record', methods=['POST'])
def save_record():
    if request.method == 'POST':
        # JSON形式で送信された記録データを受け取る
        record_data_str = request.form.get('record_data')
        if record_data_str:
            record_data = json.loads(record_data_str)
            record_date = record_data['date']

            if record_date not in game_records:
                game_records[record_date] = []
            game_records[record_date].append(record_data)

    return redirect(url_for('index')) # トップページに戻る

# --- 麻雀スコア計算ロジック（ここが肝！） ---
def calculate_mahjong_score(player_names, points, uma_settings, oka, rate):
    # 初期スコア（持ち点）は通常25000点からスタート
    initial_score = 25000

    # 各プレイヤーの最終点数を計算 (1000点単位)
    # 例: 32500点 → 32.5
    player_scores_raw = {}
    for i, name in enumerate(player_names):
        player_scores_raw[name] = (initial_score + points[i]) / 1000.0

    # スコアを降順にソートし、順位を決定
    sorted_scores = sorted(player_scores_raw.items(), key=lambda item: item[1], reverse=True)

    # 順位とウマの適用
    final_player_scores = {}
    player_ranks = {}
    rank_count = 1
    prev_score = None

    for i, (name, score) in enumerate(sorted_scores):
        if prev_score is not None and score < prev_score:
            rank_count = i + 1 # 同点の場合、同じ順位にするための調整
        player_ranks[name] = rank_count
        prev_score = score

        # 素点計算 (30000点持ち25000点返しの場合)
        # 例えば、32.5点だったら +2.5、18.0点だったら -7.0
        suten_score = (score - 30.0) # 30000点を基準に差分を計算 (1000点単位なので30.0)

        # ウマの適用
        uma_score = uma_settings.get(player_ranks[name], 0)

        # オカの適用 (1位にオカを全振り、それ以外は変動なし)
        oka_score = oka if player_ranks[name] == 1 else 0

        # 最終的なスコア (点棒移動 + ウマ + オカ)
        # 10の位で四捨五入して2桁にするために、まず1の位まで計算
        # 例: 素点2.5 + ウマ20 + オカ25 = 47.5
        # ここではまだレート適用前の「合計ポイント」を計算
        final_points_pre_rate = suten_score + uma_score + oka_score

        # 2桁のスコア形式に変換 (10点単位での四捨五入)
        # 例えば 47.5 -> 48.0
        # -7.0 -> -7.0
        # 47.5 * rate の後に四捨五入、小数点以下1桁表示
        # 最終的な表示は小数点以下1桁、例: 48.0, -7.0
        # 2桁のスコア出力、となっているので、例えば -7.0 なら -7
        # 48.0 なら +48 のようにします
        
        # ウマ・オカ・レート適用後の最終スコア（1000点単位）
        # 例: +4.8 -> +48点
        # 例: -0.7 -> -7点
        # 端数処理 (四捨五入) を考慮
        calculated_value = final_points_pre_rate * rate
        # 10の位で四捨五入 -> 1の位に四捨五入 (例: 47.5 -> 48, -7.0 -> -7)
        # ただし、レートが絡むので最終的な表示はもう少し複雑になるかも
        # 問題文の「2桁のスコアを出力」を「xx.x」ではなく「xx」と解釈し、整数部分を返す
        
        # ここでは、小数点以下1桁までを保持し、表示時に調整する
        final_player_scores[name] = round(calculated_value, 1)


    # 出力形式を整える
    formatted_results = []
    for name in player_names:
        # スコアを10倍して整数にし、さらに小数点以下を取り除く（「2桁のスコア」の解釈による）
        # 例: 47.5 -> 475 -> 48 (10点単位に丸める)
        # 最終的には、元の点数にウマ・オカ・レートを適用し、10点単位で表示する
        # ここでは、round(final_player_scores[name]) * 10 とし、小数点第一位まで保持
        display_score = round(final_player_scores[name] * 10) # 1000点単位のスコアを10倍して100点単位に
        
        formatted_results.append({
            'name': name,
            'score': display_score, # 例: 480点, -70点 (表示は「48」や「-7」にする)
            'rank': player_ranks[name]
        })

    # 順位順に並べ替え
    formatted_results.sort(key=lambda x: x['rank'])

    return formatted_results

# --- アプリケーションの実行 ---
if __name__ == '__main__':
    app.run(debug=True) # debug=Trueは開発用。変更を保存すると自動で再起動

    # --- アプリケーションの実行 ---
if __name__ == '__main__':
    # Renderは'PORT'という環境変数を使って、アプリが待ち受けるポートを指定します。
    # host='0.0.0.0' は、外部からのアクセスを許可するために必要です。
    port = int(os.getenv('PORT', 5000)) # 環境変数'PORT'があればそれを使う。なければデフォルトの5000番。
    app.run(host='0.0.0.0', port=port, debug=True)