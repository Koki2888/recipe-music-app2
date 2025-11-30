import streamlit as st
import pandas as pd
import os
import sys
from streamlit.web import cli as stcli

# --- 設定 ---
MAIN_DATA_FILE = 'recipe_music_best_matches_mahalanobis_genre.csv'
IMAGE_MAP_FILE = 'recipe_image_paths1.csv'
IMAGE_DIR_NAME = 'downloaded_images1'
MUSIC_DIR_NAME = '2025 Research Songs'


def find_resource_path(filename_or_dirname):
    """
    ファイルやフォルダを、カレントディレクトリ -> 親ディレクトリ の順で探す
    """
    # 1. スクリプトのあるディレクトリ (RecipeMusicApp/)
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base_dir = os.getcwd()

    candidate1 = os.path.join(base_dir, filename_or_dirname)
    if os.path.exists(candidate1):
        return candidate1

    # 2. 一つ上のディレクトリ (PythonProject1/)
    candidate2 = os.path.join(os.path.dirname(base_dir), filename_or_dirname)
    if os.path.exists(candidate2):
        return candidate2

    return None  # 見つからない場合


@st.cache_data(show_spinner=False)
def load_data():
    """データを読み込み、結合して返す"""

    # メインデータのパス検索
    main_path = find_resource_path(MAIN_DATA_FILE)
    if not main_path:
        return None, "Main data not found"

    try:
        df = pd.read_csv(main_path)
    except Exception:
        return None, "Error reading main data"

    # 画像マッピングデータのパス検索
    img_map_path = find_resource_path(IMAGE_MAP_FILE)
    if img_map_path:
        try:
            df_images = pd.read_csv(img_map_path)
            if 'recipe_url' in df.columns and 'recipe_url' in df_images.columns:
                df_images = df_images.drop_duplicates(subset=['recipe_url'])
                df = pd.merge(df, df_images[['recipe_url', 'image_file']], on='recipe_url', how='left')
        except Exception:
            pass  # 結合に失敗してもメインデータだけで続行

    return df, None


def main():
    st.set_page_config(
        page_title="Recipe x Music Matching App",
        page_icon="🍳",
        layout="wide"
    )

    st.markdown("""
        <style>
        .stAudio { margin-top: 10px; }
        .block-container { padding-top: 2rem; }
        img { 
            border-radius: 8px; 
            max-height: 250px;
            object-fit: cover;
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🍳 Recipe x Music Matching System 🎵")
    st.markdown("##### あなたの料理に最適な音楽を、AIが感性に基づいて推薦します。")

    df, error_msg = load_data()

    if df is None:
        st.error(f"データファイルが見つかりません: {error_msg}")
        st.info(
            "ヒント: 'recipe_music_best_matches_mahalanobis_genre.csv' がフォルダ内に存在することを確認してください。")
        return

    # 画像フォルダの実パスを探す
    real_image_dir = find_resource_path(IMAGE_DIR_NAME)
    # 音楽フォルダの実パスを探す
    real_music_dir = find_resource_path(MUSIC_DIR_NAME)

    # --- サイドバー ---
    st.sidebar.header("🔍 検索・フィルタ")

    if 'recipe_genre' in df.columns:
        unique_genres = df['recipe_genre'].dropna().unique()
        genres = ['All'] + sorted(list(unique_genres))
        selected_genre = st.sidebar.selectbox("料理ジャンルを選択", genres)
    else:
        selected_genre = 'All'

    sort_order = st.sidebar.radio("並び替え", ["類似度が高い順 (ベストマッチ)", "類似度が低い順"])

    # --- フィルタリング ---
    filtered_df = df.copy()
    if selected_genre != 'All':
        filtered_df = filtered_df[filtered_df['recipe_genre'] == selected_genre]

    if 'mutual_proximity_score(rank_sum)' in filtered_df.columns:
        if sort_order == "類似度が高い順 (ベストマッチ)":
            filtered_df = filtered_df.sort_values('mutual_proximity_score(rank_sum)', ascending=True)
        else:
            filtered_df = filtered_df.sort_values('mutual_proximity_score(rank_sum)', ascending=False)

    st.write(f"**{len(filtered_df)}** 件のレシピが見つかりました。")
    st.divider()

    # --- メインエリア ---
    for index, row in filtered_df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([1.5, 2, 2])

            # 1. 料理画像
            with col1:
                image_shown = False
                if 'image_file' in row and pd.notna(row['image_file']) and real_image_dir:
                    image_path = os.path.join(real_image_dir, str(row['image_file']))
                    if os.path.exists(image_path):
                        st.image(image_path, use_container_width=True)
                        image_shown = True

                if not image_shown:
                    st.image("https://placehold.co/600x400?text=No+Image", use_container_width=True)

            # 2. レシピ情報
            with col2:
                recipe_name = row.get('recipe_name', 'No Name')
                st.subheader(f"🍲 {recipe_name}")

                genre = row.get('recipe_genre', 'Unknown')
                st.caption(f"ジャンル: **{genre}**")

                url = row.get('recipe_url')
                if pd.notna(url):
                    st.link_button("レシピを見る ↗", url)

                score = row.get('mutual_proximity_score(rank_sum)')
                if pd.notna(score):
                    st.info(f"マッチングランク: **{int(score)}**")
                    if score <= 3.0:
                        st.markdown("**:sparkles: Best Match!**")

            # 3. 音楽情報
            with col3:
                st.markdown("### 🎵 Music")
                music_name = row.get('best_match_music_name')
                music_genre = row.get('best_match_music_genre')

                if pd.notna(music_name) and "N/A" not in str(music_name):
                    st.write(f"**{music_name}**")

                    if real_music_dir:
                        music_path = None
                        if pd.notna(music_genre):
                            path_with_genre = os.path.join(real_music_dir, str(music_genre), str(music_name))
                            if os.path.exists(path_with_genre):
                                music_path = path_with_genre

                        if music_path is None:
                            path_direct = os.path.join(real_music_dir, str(music_name))
                            if os.path.exists(path_direct):
                                music_path = path_direct

                        if music_path:
                            st.audio(music_path)
                        else:
                            st.error(f"ファイルなし: {music_name}")
                    else:
                        st.warning("音楽フォルダが見つかりません")
                else:
                    st.write("マッチする音楽がありません")

            st.divider()


if __name__ == '__main__':
    if st.runtime.exists():
        main()
    else:
        sys.argv = ["streamlit", "run", os.path.abspath(__file__)]
        sys.exit(stcli.main())