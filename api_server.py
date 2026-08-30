"""CraftLife local HTTP API — wraps database.py for the React UI (Phase 0–1)."""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import database as db
import life_api
import studio_api
from translations import get_text

_state = {
    "user_id": None,
    "token": None,
}

WEB_I18N_KEYS = [
    "app_logo", "loading", "nav_dashboard", "nav_habits", "nav_dailies",
    "nav_quests", "nav_sport", "nav_economy", "nav_health_food", "nav_shop",
    "nav_pets", "nav_guild", "nav_achievements", "nav_settings", "nav_learning",
    "nav_music", "nav_love", "nav_calendar", "nav_friends",
    "page_home_title", "page_home_subtitle", "dashboard_greeting",
    "dashboard_level", "dashboard_gold", "dashboard_hp", "dashboard_mp",
    "dashboard_streak", "web_shell_title", "web_engine_missing", "web_loading",
    "web_api_offline", "web_live_badge", "nav_adventure_menu", "nav_prestige_level",
    "web_offline_first", "web_connecting", "web_use_game_error",
    "web_legacy_ui", "web_open_web_ui",
    "web_shop_title", "web_shop_subtitle", "web_shop_tab", "web_inv_tab",
    "web_forge_tab", "web_buy", "web_buy_more", "web_sell", "web_use_item",
    "web_equip", "web_unequip", "web_forge_item", "web_inv_empty",
    "web_pet_adopt", "web_pet_feed", "web_pet_train", "web_boss_start",
    "web_boss_attack", "web_boss_skill", "web_ach_claim", "web_level_up",
    "cloud_group", "cloud_account_title", "cloud_account_info", "cloud_email",
    "cloud_password", "cloud_create_account", "cloud_signin_link",
    "cloud_credentials_invalid", "cloud_verification_sent", "cloud_account_created",
    "cloud_error", "cloud_link_account", "cloud_sync_now", "cloud_migrate_local",
    "cloud_sign_out", "cloud_status_not_configured", "cloud_status_ready_unlinked",
    "cloud_status_linked", "cloud_never", "cloud_syncing", "cloud_sync_success",
    "cloud_sync_partial", "cloud_queue_inspect", "cloud_queue_retry",
    "cloud_queue_empty", "cloud_realtime_on", "cloud_realtime_connecting",
    "cloud_personal_revision", "cloud_personal_conflict", "cloud_conflict_title",
    "cloud_conflict_hint", "cloud_conflict_keep_local", "cloud_conflict_use_remote",
    "cloud_conflict_keep_local_confirm", "cloud_conflict_use_remote_confirm",
    "cloud_conflict_resolved", "cloud_devices_title", "cloud_devices_info",
    "cloud_device_revoke", "cloud_device_revoke_others", "cloud_device_active",
    "cloud_device_revoked", "cloud_device_last_seen", "cloud_device_current_block",
    "cloud_device_register_failed", "cloud_off_hint", "cloud_shop_wallet", "web_enchant",
    "love_add_photo", "love_photo_pick_hint", "cloud_friend_username", "cloud_friend_add",
    "cloud_pvp_challenge", "cloud_chat_pick_friend", "love_daily_checkin", "love_save_checkin",
    "web_supplies_title", "web_supplies_sub", "web_supplies_add",
    "web_music_download", "web_music_search", "web_quiz_generate",
    "web_cal_day_note", "web_cal_save_note", "web_health_history",
    "web_local_account", "web_leaderboard", "web_profile", "web_create_guild", "web_join_guild",
    "web_tracker_export", "web_tracker_import", "web_check_update", "web_stay_logged_in", "web_switch_local",
    "web_task_fail", "web_task_duplicate", "web_task_folder_new", "web_supply_adjust",
    "web_sport_complete", "web_water_goal", "web_calorie_goal",
    # ── Phase P1: drag & drop reorder + quick add + undo ──
    "task_reorder_hint", "quick_add_title", "quick_add_habit", "quick_add_daily",
    "quick_add_quest", "quick_add_placeholder", "quick_add_add", "quick_add_cancel",
    "task_undo", "task_deleted", "task_restored", "task_moved_folder",
    # ── Phase P3: economy trend + supplies ──
    "economy_trend_title", "economy_trend_income", "economy_trend_expense",
    "economy_trend_net", "economy_period_7d", "economy_period_30d",
    "economy_period_90d", "economy_expense_split", "economy_trend_empty",
    "supplies_dlg_title_add", "supplies_dlg_title_edit", "supplies_name_ph",
    "supplies_category_ph", "supplies_unit_ph", "supplies_stock_lbl",
    "supplies_min_lbl", "supplies_price_lbl", "supplies_location_ph",
    "supplies_notes_ph", "supplies_economy_lbl", "supplies_stock_now",
    "supplies_tx_title", "supplies_tx_in", "supplies_tx_out",
    "supplies_tx_adjust", "supplies_qty_lbl", "supplies_note_ph",
    "supplies_restock_expense", "supplies_economy_amount",
    "supplies_economy_category_ph", "btn_save",
    "dashwidgets_title", "dashwidgets_hint", "dashwidgets_visible",
    "dashwidgets_hidden", "dashwidgets_compact", "dashwidgets_expanded",
    "dashwidgets_save", "dashwidgets_cancel", "wrapped_title", "wrapped_open",
    "wrapped_empty", "wrapped_hero", "wrapped_total", "wrapped_active_days",
    "wrapped_best", "wrapped_focus", "wrapped_level", "wrapped_streak",
    "wrapped_income", "wrapped_expense", "wrapped_top_habits", "talents_points",
    "talents_unlocked", "talents_unlock", "talents_locked_level",
    "talents_locked_prereq", "talents_no_points", "talents_tier",
    "web_retry", "web_err_action", "web_upload_too_large",
    "web_upload_bad_type", "web_upload_ok", "web_offline_gate_hint",
    # ── P3: Dashboard (rank card, stat cards, rings, insight, weekly, grafik tidur) ──
    "dashboard_progress", "dashboard_quick_actions", "dashboard_streak_days",
    "dashboard_tasks_done", "dashboard_boss_killed", "dashboard_sport_level",
    "dashboard_calories", "dashboard_habits", "dashboard_dailies",
    "dashboard_quests", "dashboard_sport", "dashboard_economy",
    "dashboard_achievements", "dashboard_level_progress", "dashboard_hp_progress",
    "dashboard_sport_progress", "dashboard_weekly_chart", "dashboard_title",
    "insights_title", "insights_no_data", "insights_top_day", "insights_best_day",
    "insights_longest", "insights_active", "insights_focus", "widget_health_chart",
    "rank_dialog_title", "rank_score_label", "rank_required_score",
    "rank_current_badge", "rank_unlocked_badge", "rank_locked_badge",
    "rank_footer_progress",
    "rank_pemula", "rank_penambang", "rank_penjelajah", "rank_petualang",
    "rank_ksatria", "rank_veteran", "rank_legenda", "rank_raja",
    "rank_penguasa_naga", "rank_dewa",
    "rank_desc_pemula", "rank_desc_penambang", "rank_desc_penjelajah",
    "rank_desc_petualang", "rank_desc_ksatria", "rank_desc_veteran",
    "rank_desc_legenda", "rank_desc_raja", "rank_desc_penguasa_naga",
    "rank_desc_dewa",
    # ── P3: Profile (foto & gelar) ──
    "title_none", "title_locked_hint", "title_selector_label",
    "profile_photo_change", "profile_photo_remove",
    "profile_photo_remove_title", "profile_photo_remove_confirm",
    # ── P3: Sport (MET, ranks, reps) ──
    "sport_rank_rookie", "sport_rank_bronze", "sport_rank_silver",
    "sport_rank_gold", "sport_rank_platinum", "sport_rank_diamond",
    "sport_rank_master", "sport_rank_mythic",
    "sport_reps_total_label", "sport_log_reps_sets", "sport_log_reps_reps",
    "sport_reps_logged", "sport_rank_up",
    "sport_reward_format", "task_streak_days",
    "sport_type_running", "sport_type_gym", "sport_type_cycling", "sport_type_swimming", "sport_type_yoga", "sport_type_football",
    "sport_type_calisthenics", "sport_type_martial_arts", "sport_type_badminton", "sport_type_other",
    "task_difficulty_easy", "task_difficulty_medium", "task_difficulty_hard", "task_difficulty_epic",
    "food_today", "food_cal_stat", "food_protein_stat", "food_carbs_stat", "food_fat_stat", "food_set_goals_btn",
    "food_calories_label", "food_protein_label", "food_carbs_label", "food_fat_label", "food_save_goals", "health_daily_targets",
    "food_tab_water", "food_water_goal_default", "food_water_set_goal", "water_progress_format", "food_water_add_250", "food_water_add_500",
    "food_water_add_1000", "food_water_custom_label", "food_water_log_title", "food_no_water_today", "food_water_goal_dialog_title", "food_water_goal_dialog_label",
    "dialog_add", "unit_ml", "unit_cm", "unit_kg", "unit_steps", "unit_hours",
    "food_bmi_title", "food_bmi_height", "food_bmi_weight", "food_bmi_age", "food_bmi_gender", "food_bmi_activity",
    "food_bmi_gender_m", "food_bmi_gender_f", "food_bmi_activity_sedentary", "food_bmi_activity_light", "food_bmi_activity_moderate", "food_bmi_activity_active",
    "food_bmi_activity_very_active", "food_bmi_save_profile", "food_bmi_calc", "food_bmi_set_target", "food_bmi_result", "food_bmi_result_format",
    "food_bmi_status_underweight", "food_bmi_status_normal", "food_bmi_status_overweight", "food_bmi_status_obese", "food_bmi_profile_saved", "food_target_updated_title",
    "food_target_updated_msg", "food_log_group_title", "food_no_logs_today", "food_meal_breakfast", "food_meal_lunch", "food_meal_dinner",
    "food_meal_snack", "food_log_name_serving", "food_nutrition_detail", "health_steps", "health_steps_value", "health_sleep",
    "health_sleep_value", "health_water", "health_water_value", "health_mood", "health_mood_value", "health_weight",
    "health_weight_value", "health_height", "health_height_value", "health_hr", "health_hr_value", "health_stress",
    "health_stress_value", "health_calories", "health_calories_value", "health_protein", "health_protein_value", "health_burned",
    "health_burned_value", "health_net_calories", "health_net_calories_value", "health_note_placeholder", "health_tab_input", "health_activity_group",
    "health_steps_label", "health_hr_label", "health_sleep_group", "health_sleep_label", "health_stress_label", "health_stress_low",
    "health_stress_normal", "health_stress_high", "health_mood_label", "health_mood_happy", "health_mood_normal", "health_mood_tired",
    "health_mood_sad", "health_notes_group", "health_notes_placeholder", "health_save", "health_data_saved", "saved_title",
    "health_avg_7days", "health_avg_7days_suffix", "health_avg_steps", "health_avg_sleep", "health_avg_water", "health_avg_hr",
    "health_unit_hour", "health_unit_ml", "health_unit_bpm", "health_weight_trend", "health_height_trend", "health_chart_weight",
    "health_chart_height", "health_tips", "health_tip_calorie_deficit", "health_tip_calorie_surplus", "health_tip_calorie_normal", "health_tip_static_1",
    "health_tip_static_2", "health_tip_static_3", "health_tip_static_4", "health_tip_static_5", "health_tip_static_6", "health_tip_static_7",
    "food_add_custom", "food_log", "food_recipes", "food_export", "food_export_format_title", "economy_export_label",
    "export_csv_option", "food_save_csv", "food_save_excel", "food_save_word", "food_save_pdf", "export_date",
    "export_calories", "export_protein", "export_carbs", "export_fat", "export_water_ml", "export_calories_burned",
    "export_net_calories", "health_nutrition_bonus_msg", "bonus_title", "level_up_bonus", "water_goal_reached",
    "rank_next_progress", "rank_max_label", "rank_view_all", "healthchart_title", "heatmap_less",
    "heatmap_more", "dashboard_recent_activity", "dashboard_xp", "title_select_label", "profile_photo_title",
    "photo_error_generic",
    "supplies_stat_items", "supplies_stat_low", "supplies_stat_value", "supplies_open_economy", "economy_open_supplies",
    "supplies_low_banner", "supplies_per_category", "supplies_history_title", "supplies_history_empty", "supplies_search_ph",
    "supplies_all_categories", "supplies_col_stock", "supplies_col_min", "supplies_col_price", "supplies_col_value",
    "supplies_empty",
    "economy_search", "economy_filter_all", "economy_filter_income", "economy_filter_expense", "economy_all_categories", "economy_folder",
    "economy_folder_label", "dialog_no_folder", "msg_name_empty", "economy_category_ph", "economy_category_hint", "economy_category_suggest",
    # WEB_I18N += P5 LovePage parity (93)
    "love_tab_overview",
    "love_tab_connection",
    "love_tab_cycle",
    "love_tab_memories",
    "love_tab_gallery",
    "love_tab_plans",
    "love_days_together",
    "love_next_moment",
    "love_connection",
    "love_my_mood",
    "love_partner_mood",
    "love_connection_score",
    "love_checkin_note_ph",
    "love_checkin_history",
    "love_upcoming",
    "love_connection_prompts",
    "love_prompt_all",
    "love_prompt_connection",
    "love_prompt_appreciation",
    "love_prompt_support",
    "love_prompt_future",
    "love_prompt_fun",
    "love_prompt_favorites",
    "love_prompt_shuffle",
    "love_prompt_favorite",
    "love_prompt_my_reflection",
    "love_prompt_my_ph",
    "love_prompt_partner_reflection",
    "love_prompt_partner_ph",
    "love_prompt_save",
    "love_prompt_history",
    "love_delete_selected",
    "love_weekly_review",
    "love_week_of",
    "love_review_appreciation_ph",
    "love_review_wins_ph",
    "love_review_support_ph",
    "love_review_intention_ph",
    "love_review_appreciation",
    "love_review_wins",
    "love_review_support",
    "love_review_intention",
    "love_review_save",
    "love_cycle_prediction",
    "love_cycle_for",
    "love_last_period",
    "love_cycle_length",
    "love_period_length",
    "love_save_cycle",
    "love_log_cycle",
    "love_cycle_history",
    "love_cycle_disclaimer",
    "love_cycle_no_data",
    "love_memories_title",
    "love_add_memory",
    "love_gallery_title",
    "love_gallery_all",
    "love_gallery_shared",
    "love_gallery_private",
    "love_gallery_upload",
    "love_gallery_select",
    "love_album_title",
    "love_album_new",
    "love_album_rename",
    "love_album_delete",
    "love_gallery_select_all",
    "love_gallery_bulk_delete",
    "love_gallery_bulk_private",
    "love_gallery_bulk_shared",
    "love_events",
    "love_add",
    "love_bucket_list",
    "love_gallery_count",
    "love_gallery_selected_count",
    "love_album_choose",
    "love_album_copy_to",
    "love_album_move_to",
    "love_album_remove",
    "love_album_personal",
    "love_gallery_delete_title",
    "love_gallery_delete_confirm",
    "love_gallery_pick_multi",
    "love_gallery_multi_result",
    "love_cycle_range",
    "love_cycle_days_until",
    "love_edit_profile",
    "love_open_tracking",
    "couple_end",
    "love_gallery_privacy_hint",
    "love_album_scope_label",
    "love_confirm",
    "love_delete",
    "love_checkin_saved",
    # WEB_I18N += P5 LovePage seluruh halaman (66)
    "berhasil_title",
    "couple_end_confirm",
    "couple_end_local_success",
    "couple_end_title",
    "couple_result_invalid_request",
    "gagal_title",
    "love_add_bucket",
    "love_add_event",
    "love_album_all",
    "love_album_copied",
    "love_album_create",
    "love_album_created",
    "love_album_delete_confirm",
    "love_album_empty",
    "love_album_err_album",
    "love_album_err_name",
    "love_album_moved",
    "love_album_name_ph",
    "love_album_no_albums",
    "love_album_removed",
    "love_album_scope",
    "love_album_shared",
    "love_album_shared_need_couple",
    "love_category",
    "love_category_date",
    "love_category_dream",
    "love_category_gift",
    "love_category_milestone",
    "love_checkin_row",
    "love_checkin_today_done",
    "love_checkin_today_none",
    "love_cloud_migration_required",
    "love_cloud_write_failed",
    "love_cloud_write_local_fallback",
    "love_couple_format",
    "love_couple_linked",
    "love_couple_not_linked",
    "love_cycle_available",
    "love_cycle_gender_notice",
    "love_date_label",
    "love_gallery_access_denied",
    "love_gallery_delete",
    "love_gallery_deselect_all",
    "love_gallery_edit",
    "love_gallery_empty",
    "love_gallery_meta",
    "love_gallery_private_hint",
    "love_gallery_shared_hint",
    "love_gallery_toggle_tip",
    "love_gallery_untitled",
    "love_health_sync",
    "love_myself",
    "love_no_upcoming",
    "love_partner_not_set",
    "love_period_end",
    "love_period_start",
    "love_prompt_answer_required",
    "love_prompt_empty_history",
    "love_prompt_no_favorites",
    "love_prompt_unfavorite",
    "love_review_empty_history",
    "love_review_required",
    "love_title_label",
    "msg_cancel",
    "msg_error",
    "msg_ok",

    # WEB_I18N += P5 prompt bank (20)
    "love_prompt_connection_seen",
    "love_prompt_connection_safe",
    "love_prompt_connection_listen",
    "love_prompt_connection_closer",
    "love_prompt_appreciation_small",
    "love_prompt_appreciation_quality",
    "love_prompt_appreciation_memory",
    "love_prompt_appreciation_growth",
    "love_prompt_support_stress",
    "love_prompt_support_request",
    "love_prompt_support_energy",
    "love_prompt_support_team",
    "love_prompt_future_year",
    "love_prompt_future_home",
    "love_prompt_future_skill",
    "love_prompt_future_priority",
    "love_prompt_fun_date",
    "love_prompt_fun_laugh",
    "love_prompt_fun_adventure",
    "love_prompt_fun_switch",

    # WEB_I18N += P5 learning studio
    "learning_export",
    "learning_export_title",
    "learning_export_done",
    "learning_export_extension_error",
    "learning_font_size",
    "learning_font_chat",
    "learning_font_studio",
    "learning_font_decrease",
    "learning_font_increase",
    "learning_font_reset",
    "learning_mindmap_invalid",

    # WEB_I18N += Learning parity keys
    "learning_history",
    "learning_view",
    "learning_rename_title",
    "learning_no_title",
    "learning_delete_gen",
    "learning_topic_label",
    "learning_upload_source",
    # WEB_I18N += P6 pomodoro parity
    "pomodoro_task_label",
    "pomodoro_task_placeholder",
    "pomodoro_focus_label",
    "pomodoro_break_label",
    "pomodoro_minutes_unit",
    "pomodoro_start",
    "pomodoro_pause",
    "pomodoro_resume",
    "pomodoro_reset",
    "pomodoro_give_up",
    "pomodoro_state_focus",
    "pomodoro_state_break",
    "pomodoro_state_idle",
    "pomodoro_complete_title",
    "pomodoro_complete_msg",
    "pomodoro_break_done",
    "pomodoro_break_done_title",
    "pomodoro_start_break",
    "pomodoro_back_to_focus",
    "pomodoro_today",
    "pomodoro_total",
    "pomodoro_stat_sessions",
    "pomodoro_stat_minutes",
    "pomodoro_recent",
    "pomodoro_no_recent",
    "pomodoro_test_alarm",
    "pomodoro_test_alarm_info",
    "level_up_msg",
    # WEB_I18N += P6 music parity
    "music_title_plain",
    "music_subtitle",
    "music_title",
    "music_select_folder",
    "music_now_playing",
    "music_play",
    "music_pause",
    "music_next",
    "music_prev",
    "music_shuffle",
    "music_repeat",
    "music_select_playlist",
    "music_playlist_label",
    "music_save_playlist",
    "music_delete_playlist",
    "music_playlist_playing",
    "music_no_tracks_to_save",
    "music_save_playlist_title",
    "music_playlist_name",
    "music_playlist_saved",
    "music_delete_playlist_confirm",
    "music_playlist_deleted",
    "music_format_error",
    "music_resource_error",
    "music_lyrics",
    "music_no_lyrics",
    "music_lyrics_not_found",
    "music_download_title",
    "music_search_web",
    "music_btn_search",
    "music_url_placeholder",
    "music_btn_download",
    "music_target_playlist",
    "music_no_results",
    "music_downloading",
    "music_download_done",
    "music_download_failed",
    "music_format_unsupported",
    "music_need_ytdlp",
    "music_lyrics_searching",
    "music_lyrics_from_file",
    "music_lyrics_from_web",
    "music_new_playlist",
    "music_add_song",
    "music_delete_playlist",
    "music_move_to_playlist",
    "music_copy_to_playlist",
    "music_remove_from_playlist",
    "music_add_files",
    "music_your_library",
    "music_now_playing_kicker",
    "music_nothing_playing",
    "music_choose_track",
    "music_search_placeholder",
    "music_track_title",
    "music_artist",
    "music_album",
    "music_duration",
    "music_track_count",
    "music_rename_playlist",
    "music_audio_filter",
    "music_unknown_artist",
    "music_unknown_album",
    "music_missing_file",
    "music_add_to_favorites",
    # WEB_I18N += P7 notes/reminder/calendar parity
    "notes_title",
    "notes_add_folder",
    "notes_add_note",
    "notes_delete",
    "notes_archive",
    "notes_save",
    "notes_title_label",
    "notes_content_label",
    "notes_no_folder",
    "notes_count_format",
    "notes_folder_label",
    "notes_list_label",
    "notes_note_title_ph",
    "notes_note_content_ph",
    "notes_saved",
    "notes_deleted",
    "notes_archived",
    "notes_unarchived",
    "notes_delete_confirm",
    "notes_folder_name",
    "notes_folder_name_ph",
    "notes_show_archived",
    "notes_hide_archived",
    "notes_archive_empty",
    "notes_add_subfolder",
    "notes_subfolder_title",
    "notes_subfolder_name",
    "notes_edit_folder_title",
    "notes_folder_delete_confirm",
    "notes_all",
    "notes_folder",
    "notes_folder_icon_default",
    "notes_folder_icon_star",
    "notes_folder_icon_heart",
    "notes_edit",
    "notes_delete",
    "notes_edit_folder",
    "notes_edit_folder_title",
    "notes_add_subfolder",
    "notes_subfolder_title",
    "notes_subfolder_name",
    "notes_all",
    "notes_no_folder",
    "notes_folder_label",
    "notes_folder_name_ph",
    "notes_folder_delete_confirm",
    "notes_folder",
    "notes_add_folder",
    "notes_folder_name",
    "notes_edit_icon",
    "notes_duplicate_folder",
    "notes_duplicate_title",
    "notes_duplicate_choose_folder",
    "notes_duplicate_btn",
    "notes_duplicate_tooltip",
    "notes_select_note_first",
    "notes_edit_icon_title",
    "notes_select_icon",
    "notes_folder_info",
    "notes_icon_updated",
    "notes_folder_renamed",
    "notes_subfolder_added",
    "notes_search_placeholder",
    "notes_search_result",
    "notes_zoom_label",
    "notes_select_icon",
    "notes_to_learning",
    "notes_to_learning_title",
    "notes_to_learning_no_note",
    "notes_to_learning_empty",
    "notes_to_learning_notebook",
    "notes_to_learning_new_nb_ph",
    "notes_to_learning_sent",
    "notes_to_learning_need_notebook",
    "notes_font_preserved",
    "notes_math_btn_tooltip",
    "notes_math_convert_sel",
    "notes_math_convert_all",
    "notes_math_preview",
    "notes_math_none",
    "notes_math_converted",
    "notes_math_preview_title",
    "notes_math_render_fail",
    "calendar_title",
    "calendar_note_title",
    "calendar_note_label",
    "calendar_note_placeholder",
    "calendar_holiday_info",
    "calendar_holiday_tooltip",
    "calendar_delete",
    "expand_all",
    "collapse_all",

    # WEB_I18N += P7 Reminders parity (dialog, repeat, sound, due)
    "confirm_title",
    "day_0",
    "day_1",
    "day_2",
    "day_3",
    "day_4",
    "day_5",
    "day_6",
    "day_fri",
    "day_fri_short",
    "day_mon",
    "day_mon_short",
    "day_sat",
    "day_sat_short",
    "day_sun",
    "day_sun_short",
    "day_thu",
    "day_thu_short",
    "day_tue",
    "day_tue_short",
    "day_wed",
    "day_wed_short",
    "dialog_save",
    "msg_no",
    "msg_yes",
    "page_reminders_subtitle",
    "page_reminders_title",
    "reminders_add",
    "reminders_add_title",
    "reminders_added",
    "reminders_alert_title",
    "reminders_browse",
    "reminders_custom_days_required",
    "reminders_custom_file_required",
    "reminders_datetime_label",
    "reminders_delete",
    "reminders_delete_confirm",
    "reminders_deleted",
    "reminders_desc_label",
    "reminders_desc_ph",
    "reminders_edit",
    "reminders_edit_title",
    "reminders_empty",
    "reminders_invalid_datetime",
    "reminders_notification",
    "reminders_past_datetime_confirm",
    "reminders_refresh",
    "reminders_repeat_custom",
    "reminders_repeat_daily",
    "reminders_repeat_label",
    "reminders_repeat_none",
    "reminders_repeat_until_label",
    "reminders_repeat_weekly",
    "reminders_select_mp3",
    "reminders_sound_beep1",
    "reminders_sound_beep2",
    "reminders_sound_custom",
    "reminders_sound_default",
    "reminders_sound_label",
    "reminders_test",
    "reminders_test_msg",
    "reminders_test_title",
    "reminders_title",
    "reminders_title_label",
    "reminders_title_ph",
    "reminders_title_required",
    "reminders_toggle",
    "reminders_updated",

    # WEB_I18N += P7 Calendar year-view parity
    "btn_cancel",
    "month_01",
    "month_02",
    "month_03",
    "month_04",
    "month_05",
    "month_06",
    "month_07",
    "month_08",
    "month_09",
    "month_10",
    "month_11",
    "month_12",
    "page_calendar_subtitle",
    "page_calendar_title",

    # WEB_I18N += P8 crafting/shop/pets parity
    "crafting_btn",
    "crafting_gold_cost",
    "crafting_gold_short",
    "crafting_have_tag",
    "crafting_missing_tag",
    "crafting_needs",
    "crafting_owned",
    "crafting_subtitle",
    "crafting_title",
    "db_enchant_max",
    "db_enchant_no_xp",
    "db_enchant_not_allowed",
    "db_enchant_success",
    "db_gold_insufficient",
    "db_pet_adopted",
    "db_pet_already_active",
    "db_pet_already_owned",
    "db_pet_equip_fail",
    "db_pet_equipped",
    "db_pet_fed",
    "db_pet_hungry",
    "db_pet_level_up",
    "db_pet_max_level",
    "db_pet_not_active",
    "db_pet_not_found",
    "db_pet_trained",
    "db_pet_unequipped",
    "enchant_btn",
    "enchant_first_btn",
    "enchant_level_tag",
    "enchant_max_tag",
    "enchant_success_title",
    "item_used_title",
    "page_crafting_subtitle",
    "page_crafting_title",
    "page_pets_subtitle",
    "page_pets_title",
    "page_shop_subtitle",
    "page_shop_title",
    "pet_active_title",
    "pet_adopted",
    "pet_already_owned",
    "pet_equipped",
    "pet_fed",
    "pet_fed_success",
    "pet_hungry",
    "pet_level_up",
    "pet_level_up_notif",
    "pet_max_level",
    "pet_not_found",
    "pet_trained",
    "pet_trained_success",
    "pet_unequipped",
    "pets_active_info",
    "pets_buff_dmg_format",
    "pets_buff_gold_format",
    "pets_buff_reduc_format",
    "pets_buff_xp_format",
    "pets_empty",
    "pets_exp_format",
    "pets_feed",
    "pets_hunger",
    "pets_level_label",
    "pets_max_1",
    "pets_max_2",
    "pets_title",
    "pets_train",
    "shop_active",
    "shop_adopt",
    "shop_buff_active",
    "shop_buff_boss_dmg",
    "shop_buff_gold",
    "shop_buff_hp_reduc",
    "shop_buff_mp",
    "shop_buff_totem",
    "shop_buff_xp",
    "shop_buy",
    "shop_buy_again",
    "shop_equip",
    "shop_no_buffs",
    "shop_owned",
    "shop_seasonal_badge",
    "shop_sell",
    "shop_sell_confirm",
    "shop_sell_price",
    "shop_sell_quantity",
    "shop_sell_title",
    "shop_tab_items",
    "shop_tab_pets",
    "shop_title",
    "shop_type_armor",
    "shop_type_consumable",
    "shop_type_legendary",
    "shop_type_special",
    "shop_type_tool",
    "shop_type_weapon",
    "shop_unequip",
    "shop_use",

    # WEB_I18N += P9 friends/guild parity
    "boss_action_block_label",
    "boss_action_block_tip",
    "boss_action_heavy_label",
    "boss_action_heavy_tip",
    "boss_action_light_label",
    "boss_action_light_tip",
    "boss_action_ultimate_label",
    "boss_action_ultimate_tip",
    "boss_appear_title",
    "boss_ultimate_name_archer",
    "boss_ultimate_name_healer",
    "boss_ultimate_name_mage",
    "boss_ultimate_name_rogue",
    "boss_ultimate_name_warrior",
    "chat_admin_block",
    "cloud_friend_accepted",
    "cloud_friend_not_linked",
    "cloud_friend_rejected",
    "cloud_friend_removed",
    "cloud_friend_request_sent",
    "cloud_friendship_not_synced",
    "cloud_pvp_claim",
    "cloud_pvp_empty",
    "cloud_pvp_finalize",
    "cloud_pvp_reward",
    "cloud_pvp_score",
    "cloud_pvp_sent",
    "couple_accept",
    "couple_cancel",
    "couple_connect",
    "couple_end_cloud_success",
    "couple_reject",
    "couple_request_accepted_notification",
    "couple_request_incoming",
    "couple_request_notification",
    "couple_request_outgoing",
    "couple_requests_title",
    "couple_result_accepted",
    "couple_result_already_couple",
    "couple_result_cancelled",
    "couple_result_error",
    "couple_result_not_friends",
    "couple_result_partner_exists",
    "couple_result_pending",
    "couple_result_rejected",
    "couple_result_self",
    "couple_status_couple",
    "couple_status_friend",
    "couple_status_pending",
    "couple_title",
    "db_boss_already_active",
    "db_boss_attack_loading",
    "db_boss_block_result",
    "db_boss_block_success",
    "db_boss_block_title",
    "db_boss_defeated",
    "db_boss_defeated_notif",
    "db_boss_hp_zero",
    "db_boss_level_too_low",
    "db_boss_no_active",
    "db_boss_not_found",
    "db_boss_reward_claimed",
    "db_boss_reward_invalid",
    "db_boss_seasonal_inactive",
    "db_boss_shield_active",
    "db_boss_started",
    "db_guild_chat_admin_cannot",
    "db_guild_chat_message",
    "db_guild_created",
    "db_guild_full",
    "db_guild_joined",
    "db_guild_kick_not_member",
    "db_guild_kick_only_leader",
    "db_guild_kick_self",
    "db_guild_kicked",
    "db_guild_kicked_notif",
    "db_guild_leader_accepted",
    "db_guild_leader_left",
    "db_guild_leader_transfer_notif",
    "db_guild_leave_admin",
    "db_guild_leave_disband",
    "db_guild_leave_not_found",
    "db_guild_leave_not_in",
    "db_guild_leave_success",
    "db_guild_leave_transfer",
    "db_guild_level_up",
    "db_guild_member_accepted",
    "db_guild_not_found",
    "db_guild_request_accept_only_leader",
    "db_guild_request_accepted_notif",
    "db_guild_request_not_found",
    "db_guild_request_notif",
    "db_guild_request_pending",
    "db_guild_request_reject_only_leader",
    "db_guild_request_rejected",
    "db_guild_request_sent",
    "db_guild_transfer_accepted",
    "db_guild_transfer_failed",
    "db_guild_transfer_invalid",
    "db_guild_transfer_not_leader",
    "db_guild_transfer_not_member",
    "db_guild_transfer_not_member_accept",
    "db_guild_transfer_old_notif",
    "db_guild_transfer_success",
    "db_mp_insufficient",
    "db_mp_insufficient_msg",
    "db_mp_insufficient_title",
    "db_mp_invalid",
    "db_raid_not_participant",
    "friends_add_btn",
    "friends_add_placeholder",
    "friends_admin_block",
    "friends_chat_btn",
    "friends_chat_unread",
    "friends_list",
    "friends_pending",
    "friends_profile_btn",
    "friends_profile_short",
    "friends_profile_title",
    "friends_remove_btn",
    "friends_title",
    "guild_accept",
    "guild_admin_warning",
    "guild_attack",
    "guild_boss_all",
    "guild_boss_atk_info",
    "guild_boss_battle",
    "guild_boss_filter",
    "guild_boss_hp",
    "guild_boss_info_format",
    "guild_boss_none",
    "guild_boss_selector_item",
    "guild_boss_tier_label",
    "guild_cant_attack",
    "guild_chat_admin_block",
    "guild_chat_message_format",
    "guild_chat_title",
    "guild_claim",
    "guild_create",
    "guild_create_btn",
    "guild_created",
    "guild_created_title",
    "guild_decs_edit_title",
    "guild_desc",
    "guild_desc_done",
    "guild_description_label",
    "guild_disbanded",
    "guild_edit_desc_btn",
    "guild_exp_progress",
    "guild_hp_zero",
    "guild_hp_zero_msg",
    "guild_id_level",
    "guild_invite_from",
    "guild_invites",
    "guild_join_request_format",
    "guild_join_requests",
    "guild_kick",
    "guild_kicked",
    "guild_leader_inherit_box",
    "guild_leader_inherit_msg",
    "guild_leader_transfer",
    "guild_leader_transfer_old",
    "guild_leave_btn",
    "guild_left",
    "guild_level_up",
    "guild_members",
    "guild_name",
    "guild_name_header",
    "guild_new_desc",
    "guild_no_guild",
    "guild_only_leader",
    "guild_quick_heal",
    "guild_reject",
    "guild_request",
    "guild_request_accepted",
    "guild_request_btn",
    "guild_request_rejected",
    "guild_request_sent",
    "guild_reward_format",
    "guild_skill_info",
    "guild_spyglass_active",
    "guild_spyglass_detail",
    "guild_start_boss",
    "guild_stats_bonus_crit",
    "guild_stats_bonus_crit_value",
    "guild_stats_bonus_damage",
    "guild_stats_bonus_damage_value",
    "guild_stats_bonus_gold",
    "guild_stats_bonus_gold_value",
    "guild_stats_bonus_xp",
    "guild_stats_bonus_xp_value",
    "guild_stats_level",
    "guild_stats_level_value",
    "guild_stats_members",
    "guild_stats_members_value",
    "guild_title",
    "guild_transfer",
    "guild_transfer_confirm_msg",
    "guild_transfer_title",
    "guild_unclaimed_rewards",
    "guild_use_skill",
    "guild_use_skill_with_icon",
    "hp_habis_title",
    "info_title",
    "level_abbr",
    "msg_enter_username",
    "page_friends_subtitle",
    "page_friends_title",
    "page_guild_subtitle",
    "page_guild_title",
    "presence_offline",
    "presence_online",
    "pvp_accept",
    "pvp_btn",
    "pvp_decline",
    "pvp_finished_lose",
    "pvp_finished_tie",
    "pvp_finished_win",
    "pvp_none",
    "pvp_pending_out",
    "pvp_score_line",
    "pvp_section",
    "raid_select_boss_first",
    "raid_start_btn",
    "raid_team_selection",
    "raid_team_selection_info",
    "raid_team_selection_title",
    "raid_ultimate_label",
    "victory_title",
    "cloud_guild_leave_confirm",
    "chat_clear_all",
    "chat_clear_all_confirm",
    "chat_send_btn",
    "register_bio",
    "register_class_label",
    "register_username",
    "register_display",
    "register_password",
    "register_confirm",
    "adopt_success",
    "chat_you",
    "chat_friend",
    "chat_message_deleted",
    "chat_reply_unavailable",
    "chat_replying_to",
    "chat_reply",
    "chat_edit",
    "chat_edit_prompt",
    "chat_delete_message",
    "chat_delete_confirm",
    "chat_react",
    "chat_remove_reaction",
    "chat_clear_self",
    "chat_clear_confirm_self",
    "chat_edited",
    "chat_download_attachment",
    "chat_pending",
    "chat_pending_action_blocked",

    "a11y_font_apply_hint", "a11y_font_scale", "a11y_group", "a11y_high_contrast", "achievement_all", "achievement_claim", "achievement_empty", "achievement_locked", "achievement_reward", "achievement_search", "achievement_unlocked", "admin_add_gold", "admin_add_xp", "admin_complete_tasks", "admin_debug_title", "admin_export_blocked", "admin_fill_hp_mp", "admin_hp_restored", "admin_import_blocked", "admin_max_level", "admin_mode_active", "admin_mode_msg", "admin_mode_title", "admin_panel", "admin_pet_add_exp", "admin_pet_cheat", "admin_pet_feed", "admin_pet_level_up", "admin_tasks_done", "admin_warning", "cheat_title", "currency_idr", "debug_gold_added", "debug_hp_mp_restored", "debug_level_already", "debug_level_set", "debug_tasks_done", "debug_title", "debug_xp_added", "export_failed", "export_generic_error", "export_history_action", "export_history_date", "export_history_task_id", "export_history_type", "export_lib_docx", "export_lib_missing", "export_lib_openpyxl", "export_lib_reportlab", "export_metric", "export_section_dailies", "export_section_economy", "export_section_economy_items", "export_section_habits", "export_section_health", "export_section_health_log", "export_section_history", "export_section_quests", "export_section_sport", "export_section_stats", "export_section_user", "export_success", "export_value", "import_confirm_warning", "import_failed", "import_success", "lang_en", "lang_id", "leaderboard_col_gold", "leaderboard_col_level", "leaderboard_col_pet", "leaderboard_col_rebirth", "leaderboard_col_sport", "leaderboard_col_user", "leaderboard_col_xp", "leaderboard_partner_tip", "leaderboard_single_tip", "nav_leaderboard", "redeem_admin_password_prompt", "redeem_admin_password_title", "redeem_admin_password_wrong", "reset_answer_empty", "reset_answer_wrong", "reset_backup_code_label", "reset_backup_reset_btn", "reset_bc_empty", "reset_bc_invalid", "reset_cancel", "reset_confirm_btn", "reset_confirm_detail", "reset_confirm_invalid", "reset_confirm_placeholder", "reset_confirm_title", "reset_confirm_type_label", "reset_confirm_warning", "reset_error", "reset_loading", "reset_method_backup", "reset_method_security", "reset_method_title", "reset_no_bc", "reset_no_bc_long", "reset_no_sq", "reset_password_answer", "reset_password_backup_btn", "reset_password_backup_code", "reset_password_backup_title", "reset_password_btn", "reset_password_check", "reset_password_confirm", "reset_password_new", "reset_password_security_question", "reset_password_security_title", "reset_password_username", "reset_password_verify", "reset_success_msg", "reset_success_title", "reset_username_empty", "reset_username_notfound", "reset_verify_password_prompt", "reset_verify_password_title", "settings_backup_now", "settings_change_restart_msg", "settings_currency", "settings_data_management", "settings_database", "settings_db_path", "settings_exit", "settings_exit_btn", "settings_export_tracker", "settings_import_tracker", "settings_language", "settings_language_en", "settings_language_id", "settings_language_restart_msg", "settings_language_restart_no", "settings_language_restart_title", "settings_language_restart_yes", "settings_reset_btn", "settings_reset_progress", "settings_reset_warning", "settings_sound", "settings_sound_enable", "settings_sound_hint", "settings_theme", "settings_theme_changed", "settings_theme_title", "settings_title", "unit_exp", "unit_gold", "unit_xp", "update_apply", "update_auto_countdown", "update_available", "update_available_title", "update_check", "update_check_offline", "update_checking", "update_downloading", "update_failed", "update_group_title", "update_later", "update_latest", "update_notes_label", "update_restarting", "update_version",

    "cloud_leaderboard_events", "cloud_leaderboard_exp", "cloud_leaderboard_guild", "cloud_leaderboard_local", "cloud_leaderboard_members", "cloud_leaderboard_points", "cloud_leaderboard_productivity", "leaderboard_guild", "leaderboard_rank", "leaderboard_title",

    "achievement_category_boss", "achievement_category_crafting", "achievement_category_daily", "achievement_category_economy", "achievement_category_focus", "achievement_category_guild", "achievement_category_habit", "achievement_category_health", "achievement_category_level", "achievement_category_nutrition", "achievement_category_pet", "achievement_category_social", "achievement_category_special", "achievement_category_sport", "achievement_category_todo", "achievement_claimed", "achievement_progress_format", "achievement_reward_format",

    "web_hero_custom", "web_hero_avatar", "web_hero_name", "web_hero_class", "web_hero_bio", "web_profile_saved", "web_profile_save", "reload_now_confirm",

    "btn_close", "food_meal_type", "health_mood_low", "learning_no_notebook", "nav_notes", "nav_pomodoro", "notes_color", "notes_default_title", "notes_denominator", "notes_empty", "notes_fraction", "notes_fraction_title", "notes_highlight", "notes_numerator", "notes_select_hint", "notes_symbols", "notes_to_learning_done", "notes_unarchive", "notes_unsaved", "notes_updated", "pomodoro", "sport_activity_ph", "sport_calories_label", "sport_rank_max", "sport_rank_progress", "sport_type_label", "supplies_add", "web_backup_code", "web_display_name", "web_forgot_password", "web_have_account", "web_login_btn", "web_login_subtitle", "web_need_account", "web_palette_placeholder", "web_password", "web_register_btn", "web_register_subtitle", "web_username",
]







def configure(user_id: int, token: str | None = None) -> None:
    _state["user_id"] = int(user_id)
    _state["token"] = token


def _json_bytes(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")


def _row_user(u: dict) -> dict:
    if not u:
        return {}
    level = int(u.get("level") or 1)
    cls = (u.get("avatar_class") or "warrior").lower()
    if cls == "archer":
        cls = "ranger"
    ice = 0
    try:
        for row in db.get_inventory(u.get("id")):
            if row.get("item_id") == "ice_block":
                ice += int(row.get("quantity") or 0)
    except Exception:
        ice = 0
    active_pet = None
    try:
        for p in db.get_user_pets(u.get("id")):
            if p.get("is_active"):
                active_pet = p.get("pet_id")
                break
    except Exception:
        pass
    has_photo = False
    try:
        has_photo = db.get_profile_photo(u.get("id")) is not None
    except Exception:
        has_photo = False
    return {
        "id": str(u.get("id")),
        "username": u.get("username") or "",
        "displayName": u.get("display_name") or u.get("username") or "",
        "name": u.get("display_name") or "",
        "bio": u.get("bio") or "",
        "avatarClass": cls if cls in ("warrior", "mage", "rogue", "paladin", "ranger", "healer") else "warrior",
        "heroClass": u.get("avatar_class") or "warrior",
        "avatarEmoji": u.get("avatar_emoji") or "⚔️",
        "avatar": u.get("avatar_emoji") or "⚔️",
        "avatarColor": u.get("avatar_color") or "#ef4444",
        "level": level,
        "xp": int(u.get("xp") or 0),
        "xpToNextLevel": level * 150,
        "hp": int(u.get("hp") or 0),
        "maxHp": int(u.get("max_hp") or 50),
        "mp": int(u.get("mp") or 0),
        "maxMp": int(u.get("max_mp") or 30),
        "gold": int(round(float(u.get("gold") or 0))),
        "gems": int(u.get("gems") or 0),
        "rebirthCount": int(u.get("rebirth_count") or 0),
        "sportLevel": int(u.get("sport_level") or 1),
        "sportXp": int(u.get("sport_xp") or 0),
        "activePetId": active_pet,
        "equippedWeapon": None,
        "equippedArmor": None,
        "equippedTool": None,
        "equippedLegendary": None,
        "freezeSlots": ice,
        "createdAt": u.get("created_at") or "",
        "language": u.get("language") or "id",
        "theme": u.get("theme") or "modern_dark",
        "soundEnabled": bool(u.get("sound_enabled", 1)),
        "longestStreak": int(u.get("longest_streak") or 0),
        "guildId": u.get("guild_id"),
        "currency": u.get("currency") or "IDR",
        "selectedTitle": u.get("selected_title") or "",
        "hasProfilePhoto": has_photo,
        "fontScale": int(u.get("font_scale") or 100),
        "highContrast": bool(u.get("high_contrast")),
        "isAdmin": bool(u.get("is_admin")),
        "hasSpyglass": bool(u.get("has_spyglass")),
        "onboardingDone": bool(u.get("onboarding_done")),
        # Parity GuildPage._attack attack-info line: atk = 25 + bonus buff damage.
        "bossDamageBonus": int(u.get("boss_damage_bonus") or 0),
        "hpDamageReduction": int(u.get("hp_damage_reduction") or 0),
        "mpBonus": int(u.get("mp_bonus") or 0),
    }


def _map_habit(h: dict) -> dict:
    diff = (h.get("difficulty") or "medium").lower()
    if diff not in ("trivial", "easy", "medium", "hard", "epic"):
        diff = "medium"
    return {
        "id": str(h.get("id")),
        "title": h.get("name") or "",
        "notes": h.get("notes") or "",
        "folderId": str(h["folder_id"]) if h.get("folder_id") else None,
        "difficulty": diff,
        "isPositive": bool(h.get("positive", 1)),
        "isNegative": bool(h.get("negative", 0)),
        "positiveStreak": int(h.get("streak") or h.get("counter_up") or 0),
        "negativeStreak": int(h.get("counter_down") or 0),
        "history": [],
        "createdAt": h.get("created_at") or "",
        "icon": h.get("icon") or "⚔️",
        "doneToday": bool(h.get("done_today")),
        "sortOrder": int(h.get("sort_order") or 0),
    }


def _parse_repeat(raw) -> list:
    if not raw:
        return [0, 1, 2, 3, 4, 5, 6]
    s = str(raw)
    days = []
    for part in s.replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            days.append((int(part) + 1) % 7)
    return sorted(set(days)) or [0, 1, 2, 3, 4, 5, 6]


def _repeat_to_db(days) -> str:
    """Konvensi JS getDay (0=Minggu..6=Sabtu) → Python weekday untuk simpan
    repeat_days. Semua 7 hari terpilih = string kosong (parity WeekdaySelector:
    kosong berarti tiap hari)."""
    valid = sorted({(int(d) + 6) % 7 for d in days if 0 <= int(d) <= 6})
    if not valid or len(valid) == 7:
        return ""
    return ",".join(str(d) for d in valid)


def _dashboard_summary(uid):
    """/api/dashboard/summary — rank, statistik, insight, grafik tidur↔produktivitas,
    weekly XP/gold, target & kalori hari ini, berat terakhir.
    Parity DashboardPage PyQt (_rank_card, stat cards, progress rings,
    _refresh_insights, _refresh_health_chart)."""
    s = db.get_stats(uid)
    u = s.get("user") or {}
    weight_kg = 65.0
    try:
        conn = db.get_conn()
        rw = conn.execute(
            "SELECT weight_kg FROM health_logs WHERE user_id=? AND weight_kg IS NOT NULL ORDER BY log_date DESC LIMIT 1",
            (uid,),
        ).fetchone()
        conn.close()
        if rw and rw["weight_kg"]:
            weight_kg = float(rw["weight_kg"])
    except Exception:
        pass
    try:
        goals = db.get_nutrition_goals(uid) or {}
        cal_goal = int(goals.get("daily_calories") or 2000)
    except Exception:
        cal_goal = 2000
    try:
        cal_today = int((db.get_nutrition_summary(uid) or {}).get("calories") or 0)
    except Exception:
        cal_today = 0
    try:
        rank = db.calculate_rank(uid)
    except Exception:
        rank = {}
    try:
        insights = db.get_insights(uid)
    except Exception:
        insights = {"has_data": False}
    try:
        health_chart = db.get_health_productivity_series(uid)
    except Exception:
        health_chart = {"series": [], "correlation": 0.0, "days_with_sleep_data": 0}
    return {
        "ok": True,
        "rank": {
            "rank": int(rank.get("rank") or 0),
            "icon": rank.get("rank_icon") or "🥚",
            "nameKey": rank.get("rank_name_key") or "rank_pemula",
            "descKey": rank.get("rank_desc_key") or "rank_desc_pemula",
            "score": int(rank.get("score") or 0),
            "maxScore": int(rank.get("max_score") or 100),
        },
        "stats": {
            "maxStreak": int(s.get("max_streak") or 0),
            "bossesKilled": int(s.get("bosses_killed") or 0),
            "totalTasksCompleted": int(u.get("total_tasks_completed") or 0),
            "habitsDoneToday": int(s.get("habits_done_today") or 0),
            "habitsTotal": int(s.get("habits_total") or 0),
            "dailiesDoneToday": int(s.get("dailies_done_today") or 0),
            "dailiesTotal": int(s.get("dailies_total") or 0),
            "todosDone": int(s.get("todos_done") or 0),
            "todosTotal": int(s.get("todos_total") or 0),
        },
        "caloriesToday": cal_today,
        "calorieGoal": cal_goal,
        "weightKg": weight_kg,
        "insights": insights,
        "healthChart": {
            "series": [
                {"date": d, "sleep": sl, "tasks": tk}
                for d, sl, tk in (health_chart.get("series") or [])
            ],
            "correlation": float(health_chart.get("correlation") or 0.0),
            "daysWithSleepData": int(health_chart.get("days_with_sleep_data") or 0),
        },
        "weekly": s.get("weekly") or [],
    }


def _map_daily(d: dict) -> dict:
    diff = (d.get("difficulty") or "medium").lower()
    if diff not in ("trivial", "easy", "medium", "hard", "epic"):
        diff = "medium"
    return {
        "id": str(d.get("id")),
        "title": d.get("name") or "",
        "notes": d.get("notes") or "",
        "folderId": str(d["folder_id"]) if d.get("folder_id") else None,
        "difficulty": diff,
        "streak": int(d.get("streak") or 0),
        "isCompletedToday": bool(d.get("done_today")),
        "repeatDays": _parse_repeat(d.get("repeat_days")),
        "lastCompletedDate": d.get("last_done"),
        "isFrozen": int(d.get("freeze_slots") or 0) > 0,
        "createdAt": d.get("created_at") or "",
        "icon": d.get("icon") or "📅",
        "sortOrder": int(d.get("sort_order") or 0),
    }


def _map_todo(t: dict) -> dict:
    prio = (t.get("priority") or "medium").lower()
    if prio not in ("trivial", "easy", "medium", "hard", "epic"):
        prio = "medium"
    return {
        "id": str(t.get("id")),
        "title": t.get("name") or "",
        "notes": t.get("notes") or "",
        "folderId": str(t["folder_id"]) if t.get("folder_id") else None,
        "difficulty": prio,
        "dueDate": t.get("due_date"),
        "isCompleted": bool(t.get("done")),
        "completedAt": None,
        "createdAt": t.get("created_at") or "",
        "icon": t.get("icon") or "📜",
        "sortOrder": int(t.get("sort_order") or 0),
    }


def _map_inv(row: dict) -> dict:
    return {
        "itemId": row.get("item_id"),
        "quantity": int(row.get("quantity") or 1),
        "equipped": bool(row.get("equipped")),
        "rowId": row.get("id"),
        "enchantLevel": int(row.get("enchant_level") or 0),
    }


def _map_pet(row: dict) -> dict:
    return {
        "petId": row.get("pet_id"),
        "nickname": row.get("nickname") or row.get("pet_id"),
        "level": int(row.get("level") or 1),
        "xp": int(row.get("exp") or row.get("xp") or 0),
        "hunger": int(row.get("hunger") or 100),
        "isEquipped": bool(row.get("is_active")),
        "adoptedAt": row.get("adopted_at") or "",
    }


def _leaderboard_title_loc(key: str, uid: int) -> str:
    """Parity LeaderboardPage: map title key → nama terlokalisasi (db.TITLES)."""
    if not key:
        return ""
    try:
        u = db.get_user(uid) or {}
        lang = u.get("language") or "id"
        tmap = {t["key"]: (t["name"][0] if lang == "id" else t["name"][1]) for t in db.TITLES}
        return tmap.get(key, "")
    except Exception:
        return ""


def _map_ach(row: dict) -> dict:
    unlocked = bool(row.get("unlocked_at"))
    try:
        _lang = (db.get_user(_state.get("user_id") or 0) or {}).get("language") or "id"
        _t_name, _t_desc = db.tr_achievement(row, _lang)
    except Exception:
        _t_name, _t_desc = row.get("name") or "", row.get("description") or ""
    return {
        "id": str(row.get("id")),
        "title": _t_name,
        "desc": _t_desc,
        "rawName": row.get("name") or "",
        "rawDesc": row.get("description") or "",
        "category": row.get("category") or "level",
        "icon": row.get("icon") or "🏆",
        "xpReward": int(row.get("xp_reward") or 0),
        "goldReward": int(row.get("gold_reward") or 0),
        "currentProgress": int(row.get("progress") or 0),
        "targetProgress": int(row.get("requirement_value") or 1),
        "isUnlocked": unlocked,
        "isClaimed": bool(row.get("claimed")),
    }


def _shop_catalog() -> list:
    out = []
    for iid, item in getattr(db, "SHOP_ITEMS", {}).items():
        rec = dict(item)
        rec["id"] = iid
        rec["buffDesc"] = rec.pop("buff_desc", rec.get("buffDesc", ""))
        rec["craftOnly"] = bool(rec.get("craftOnly") or rec.get("craft_only"))
        rec["seasonal"] = rec.get("seasonal") or ""
        # Parity ShopPage.load: db.is_shop_item_visible (craft_only tersembunyi,
        # seasonal hanya saat window event aktif).
        try:
            rec["visible"] = bool(db.is_shop_item_visible(iid))
        except Exception:
            rec["visible"] = not rec["craftOnly"]
        out.append(rec)
    return out


def _pet_catalog() -> list:
    out = []
    for pid, pet in getattr(db, "PETS_DATA", {}).items():
        rec = dict(pet)
        rec["id"] = pid
        rec["baseBuff"] = rec.pop("base_buff", rec.get("baseBuff", {}))
        out.append(rec)
    return out


def _boss_catalog() -> list:
    out = []
    for bid, b in getattr(db, "BOSSES", {}).items():
        rec = dict(b)
        rec["id"] = bid
        rec["maxHp"] = rec.get("hp")
        rec["xpReward"] = rec.get("xp") or rec.get("xpReward")
        rec["goldReward"] = rec.get("gold") or rec.get("goldReward")
        rec["minLevel"] = rec.get("min_level") or rec.get("minLevel") or 1
        out.append(rec)
    return out


def _recipe_catalog() -> list:
    out = []
    for rid, r in getattr(db, "CRAFTING_RECIPES", {}).items():
        inputs = r.get("inputs") or []
        req = [{"itemId": i, "quantity": 1} for i in inputs]
        desc = r.get("desc") or ("", "")
        out.append({
            "id": rid,
            "resultItemId": r.get("output") or rid,
            "requiredItems": req,
            "goldCost": int(r.get("gold") or 0),
            # Parity CraftingPage: desc dipilih per bahasa user.
            "descId": desc[0] if len(desc) > 0 else "",
            "descEn": desc[1] if len(desc) > 1 else desc[0] if desc else "",
        })
    return out


def _snapshot(uid: int) -> dict:
    u = db.get_user(uid) or {}
    try:
        ach = [_map_ach(a) for a in db.get_user_achievements(uid)]
    except Exception:
        ach = []
    try:
        inv = [_map_inv(r) for r in db.get_inventory(uid)]
    except Exception:
        inv = []
    try:
        pets = [_map_pet(r) for r in db.get_user_pets(uid)]
    except Exception:
        pets = []
    payload = {
        "user": _row_user(u),
        "habits": [_map_habit(h) for h in db.get_habits(uid)],
        "dailies": [_map_daily(d) for d in db.get_dailies(uid)],
        "quests": [_map_todo(t) for t in db.get_todos(uid)],
        "inventory": inv,
        "userPets": pets,
        "achievements": ach,
        "lang": u.get("language") or "id",
        # Parity ShopPage._buff_bar: daftar string buff aktif apa adanya dari db.
        "activeBuffs": db.get_all_active_buffs(uid),
    }
    payload.update(life_api.snapshot(uid))
    payload.update(studio_api.snapshot(uid))
    try:
        battle = db.get_active_boss_for_user(uid)
    except Exception:
        battle = None
    if battle:
        payload["activeBoss"] = {
            "id": battle.get("boss_id") or "",
            "name": battle.get("boss_name") or "",
            "icon": battle.get("boss_icon") or "🐉",
            "tier": battle.get("boss_tier") or "normal",
            "hp": int(battle.get("boss_max_hp") or battle.get("boss_hp") or 0),
            "maxHp": int(battle.get("boss_max_hp") or battle.get("boss_hp") or 0),
            "atk": int(battle.get("boss_attack") or 0),
            "xpReward": 0,
            "goldReward": 0,
            "minLevel": 1,
        }
        payload["activeBossHp"] = int(battle.get("boss_hp") or 0)
        payload["activeBossId"] = battle.get("boss_id")
    else:
        payload["activeBoss"] = None
        payload["activeBossHp"] = 0
        payload["activeBossId"] = None
    link = None
    try:
        link = db.get_cloud_user_link(uid)
    except Exception:
        link = None
    wallet = None
    if link:
        try:
            wallet = db.get_cloud_wallet(uid)
        except Exception:
            wallet = None
        gold_cloud = int((wallet or {}).get("gold") or 0) if wallet else None
        payload["user"]["cloudLinked"] = True
        payload["user"]["goldLocal"] = payload["user"]["gold"]
        payload["user"]["goldCloud"] = gold_cloud
        payload["goldLocal"] = payload["user"]["gold"]
        payload["goldCloud"] = gold_cloud
        payload["cloudLinked"] = True
        if gold_cloud is not None:
            payload["user"]["gold"] = gold_cloud
            if wallet and wallet.get("gems") is not None:
                payload["user"]["gems"] = int(wallet.get("gems") or 0)
        try:
            cloud_inv = db.get_cloud_inventory_cache(uid)
        except Exception:
            cloud_inv = []
        if cloud_inv:
            payload["inventory"] = [
                _map_inv({
                    "item_id": row.get("item_key"),
                    "quantity": row.get("qty") or 0,
                    "equipped": row.get("equipped"),
                    "id": row.get("item_key"),
                    "enchant_level": row.get("enchant_level") or 0,
                })
                for row in cloud_inv
                if int(row.get("qty") or 0) > 0
            ]
    else:
        payload["goldLocal"] = payload["user"]["gold"]
        payload["goldCloud"] = None
        payload["cloudLinked"] = False
        payload["user"]["goldLocal"] = payload["user"]["gold"]
        payload["user"]["goldCloud"] = None
        payload["user"]["cloudLinked"] = False
    return payload


def _ok_payload(uid: int, result=None, extra=None) -> dict:
    payload = {"ok": True, "result": result or {}}
    payload.update(_snapshot(uid))
    if extra:
        payload.update(extra)
    if isinstance(result, dict) and result.get("leveled_up"):
        payload["levelUp"] = {
            "level": result.get("new_level"),
            "hpGain": 15,
            "mpGain": 10,
            "goldGain": result.get("gold_gained") or 0,
        }
    return payload


def _equip_item(uid: int, item_id: str, equipped: bool) -> dict:
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM inventory WHERE user_id=? AND item_id=?",
            (uid, item_id),
        ).fetchone()
        if not row:
            return {"ok": False, "msg": "not_found"}
        item = db.SHOP_ITEMS.get(item_id) or {}
        itype = item.get("type")
        if equipped and itype:
            conn.execute(
                """UPDATE inventory SET equipped=0 WHERE user_id=? AND item_id IN
                   (SELECT item_id FROM inventory WHERE user_id=?)""",
                (uid, uid),
            )
            # only unequip same type
            rows = conn.execute("SELECT item_id FROM inventory WHERE user_id=?", (uid,)).fetchall()
            for r in rows:
                meta = db.SHOP_ITEMS.get(r["item_id"]) or {}
                if meta.get("type") == itype:
                    conn.execute(
                        "UPDATE inventory SET equipped=0 WHERE user_id=? AND item_id=?",
                        (uid, r["item_id"]),
                    )
        conn.execute(
            "UPDATE inventory SET equipped=? WHERE user_id=? AND item_id=?",
            (1 if equipped else 0, uid, item_id),
        )
        conn.commit()
    finally:
        conn.close()
    if hasattr(db, "recalculate_all_buffs"):
        db.recalculate_all_buffs(uid)
    return {"ok": True}


def _ensure_user() -> int | None:
    uid = _state.get("user_id")
    if uid:
        return int(uid)
    try:
        conn = db.get_conn()
        row = conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
        conn.close()
        if row:
            _state["user_id"] = int(row["id"])
            return int(row["id"])
    except Exception:
        return None
    return None


def _auth_ok(handler) -> bool:
    uid = _ensure_user()
    if not uid:
        return False
    token = _state.get("token")
    hdr = handler.headers.get("Authorization") or ""
    qtoken = parse_qs(urlparse(handler.path).query).get("token", [None])[0]
    given = None
    if hdr.lower().startswith("bearer "):
        given = hdr[7:].strip()
    elif qtoken:
        given = qtoken
    if token and given and given != token:
        return False
    return True


def _guild_id(uid: int):
    u = db.get_user(uid) or {}
    return u.get("guild_id")


_UPLOAD_IMAGE_MAX = 8 * 1024 * 1024
_UPLOAD_AUDIO_MAX = 25 * 1024 * 1024


def _learning_sources_dir() -> str:
    """Folder penyimpanan file sumber Learning (parity path PyQt di data root)."""
    try:
        root = db.get_data_root()  # type: ignore[attr-defined]
    except Exception:
        root = os.path.dirname(os.path.abspath(db.DB_PATH)) if getattr(db, "DB_PATH", "") else os.getcwd()
    d = os.path.join(root, "learning_sources")
    os.makedirs(d, exist_ok=True)
    return d


def _safe_upload_name(name: str, default_ext: str) -> str:
    base = os.path.basename(name or "") or "upload" + default_ext
    base = re.sub(r"[^A-Za-z0-9._\- ]+", "_", base).strip(" .")
    return base or ("upload" + default_ext)


def _prepare_upload_image(raw: bytes, max_side: int):
    """Normalisasi foto upload web — parity _prepare_image_file/_ImagePickerDialog PyQt
    (decode, hormati EXIF orientation, batas 32..4096, downscale ≤ max_side, re-encode
    JPEG q88). Return (bytes, "image/jpeg", w, h) atau None bila bukan gambar valid.
    """
    try:
        import io as _io
        from PIL import Image, ImageOps
        with Image.open(_io.BytesIO(raw)) as im:
            im.load()
            im = ImageOps.exif_transpose(im)
            w, h = im.size
            if not (32 <= w <= 4096 and 32 <= h <= 4096):
                return None
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            im.thumbnail((max_side, max_side), Image.LANCZOS)
            buf = _io.BytesIO()
            im.save(buf, "JPEG", quality=88)
            return buf.getvalue(), "image/jpeg", im.width, im.height
    except Exception:
        return None


def _handle_upload_file(uid: int, body: dict) -> dict:
    """POST /api/upload/file  {target, name, dataBase64}

    target: love_photo | profile_photo | reminder_sound | music
    Return dict 'result' yang dibungkus _ok_payload oleh caller.
    """
    import base64
    target = (body.get("target") or "").strip()
    raw_b64 = body.get("dataBase64") or ""
    try:
        raw = base64.b64decode(raw_b64, validate=True)
    except Exception:
        return {"ok": False, "error": "invalid_base64", "msg": "invalid_base64"}
    if not raw:
        return {"ok": False, "error": "empty_file", "msg": "empty_file"}

    if target in ("love_photo", "profile_photo"):
        if len(raw) > _UPLOAD_IMAGE_MAX:
            return {"ok": False, "error": "file_too_large", "msg": "web_upload_too_large"}
        max_side = 1280 if target == "love_photo" else 768
        prepared = _prepare_upload_image(raw, max_side)
        if not prepared:
            return {"ok": False, "error": "bad_type", "msg": "web_upload_bad_type"}
        blob, mime, w, h = prepared
        if target == "love_photo":
            import cloud_api as ca
            # Parity LovePage._GalleryPhotoDialog: metadata (caption/date/visibility) ikut
            # saat upload; visibilitas 'shared' hanya valid bila couple aktif.
            try:
                _ctx = db.get_couple_context(uid) or {}
                _couple_active = bool(_ctx.get("active"))
            except Exception:
                _couple_active = False
            vis = "shared" if ((body.get("visibility") or "private") == "shared" and _couple_active) else "private"
            pdate = (body.get("photoDate") or body.get("photo_date") or "").strip() or None
            return ca.love_photo_from_bytes(
                uid, blob, mime,
                caption=(body.get("caption") or "").strip() or None,
                photo_date=pdate,
                visibility=vis,
            )
        result = db.set_profile_photo(uid, uid, blob, mime, w, h)
        if result.get("ok"):
            try:
                if db.get_cloud_user_link(uid):
                    from sync_service import get_sync_service
                    get_sync_service().queue_profile_photo(uid)
            except Exception:
                pass
        return result

    if target in ("reminder_sound", "music"):
        if len(raw) > _UPLOAD_AUDIO_MAX:
            return {"ok": False, "error": "file_too_large", "msg": "web_upload_too_large"}
        name = _safe_upload_name(body.get("name") or "", ".mp3")
        ext = os.path.splitext(name)[1].lower()
        if ext not in (".mp3", ".m4a", ".ogg", ".wav", ".opus", ".flac", ".mp4"):
            return {"ok": False, "error": "bad_type", "msg": "web_upload_bad_type"}
        try:
            import music_downloader as md
            lib_dir = md.get_download_dir()
        except Exception:
            lib_dir = os.path.join(os.path.expanduser("~"), "Music", "CraftLife")
            os.makedirs(lib_dir, exist_ok=True)
        sub = "reminder_sounds" if target == "reminder_sound" else ""
        dest_dir = os.path.join(lib_dir, sub) if sub else lib_dir
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, f"{uuid.uuid4().hex[:8]}_{name}")
        with open(dest, "wb") as f:
            f.write(raw)
        return {"ok": True, "path": dest, "name": os.path.basename(dest)}

    if target == "learning_source":
        # Parity LovePage._add_source_files: .txt/.md/.pdf/.docx, word-count >=
        # LEARNING_MIN_SOURCE_WORDS divalidasi di studio_api.add_learning_source.
        _LEARN_MAX = 20 * 1024 * 1024
        if len(raw) > _LEARN_MAX:
            return {"ok": False, "error": "file_too_large", "msg": "web_upload_too_large"}
        name = _safe_upload_name(body.get("name") or "", ".txt")
        ext = os.path.splitext(name)[1].lower()
        if ext not in (".txt", ".md", ".pdf", ".docx"):
            return {"ok": False, "error": "bad_type", "msg": "web_upload_bad_type"}
        sdir = _learning_sources_dir()
        dest = os.path.join(sdir, f"{uuid.uuid4().hex[:8]}_{name}")
        with open(dest, "wb") as f:
            f.write(raw)
        return {"ok": True, "path": dest, "name": os.path.basename(dest)}

    return {"ok": False, "error": "unknown_target", "msg": "web_upload_bad_type"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _cors(self):
        origin = self.headers.get("Origin") or "*"
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Credentials", "true")

    def _send(self, code, payload, content="application/json"):
        body = payload if isinstance(payload, bytes) else _json_bytes(payload)
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", content + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/api/health":
            self._send(200, {"ok": True, "phase": 1})
            return

        if path.startswith("/assets/") or path in ("/", "/index.html"):
            self._serve_static(path)
            return

        # Stream a local library audio file to the browser <audio> element.
        # The path is validated to live inside the CraftLife Music folder, so a
        # web client can "play a local file" (parity with PyQt QMediaPlayer),
        # and stays local — the file is never uploaded anywhere.
        if path == "/music/stream":
            file_path = (qs.get("path") or [""])[0]
            self._serve_audio(file_path)
            return

        if not _auth_ok(self) and path.startswith("/api/") and path != "/api/health":
            if path != "/api/i18n":
                self._send(401, {"ok": False, "error": "unauthorized"})
                return

        uid = _state.get("user_id")
        if path == "/api/i18n":
            lang = (qs.get("lang") or ["id"])[0]
            if lang not in ("id", "en"):
                lang = "id"
            keys = qs.get("keys")
            out = {}
            source_keys = keys[0].split(",") if keys else WEB_I18N_KEYS
            for k in source_keys:
                k = k.strip()
                if k:
                    out[k] = get_text(k, lang)
            self._send(200, {"lang": lang, "messages": out})
            return

        routes = {
            "/api/me": lambda: {"ok": True, "user": _row_user(db.get_user(uid))},
            "/api/habits": lambda: {"ok": True, "habits": [_map_habit(h) for h in db.get_habits(uid)]},
            "/api/dailies": lambda: {"ok": True, "dailies": [_map_daily(d) for d in db.get_dailies(uid)]},
            "/api/todos": lambda: {"ok": True, "quests": [_map_todo(t) for t in db.get_todos(uid)]},
            "/api/inventory": lambda: {"ok": True, "inventory": [_map_inv(r) for r in db.get_inventory(uid)]},
            "/api/pets": lambda: {"ok": True, "userPets": [_map_pet(r) for r in db.get_user_pets(uid)]},
            "/api/achievements": lambda: {"ok": True, "achievements": [_map_ach(a) for a in db.get_user_achievements(uid)]},
            "/api/catalog/shop": lambda: {"ok": True, "items": _shop_catalog()},
            "/api/catalog/pets": lambda: {"ok": True, "pets": _pet_catalog()},
            "/api/catalog/bosses": lambda: {"ok": True, "bosses": _boss_catalog()},
            "/api/catalog/recipes": lambda: {"ok": True, "recipes": _recipe_catalog()},
            "/api/catalog/currency": lambda: {"ok": True, "rates": getattr(db, "CURRENCY_RATES", {"IDR": 1})},
            "/api/catalog/enchant": lambda: {"ok": True,
                "maxLevel": getattr(db, "ENCHANT_MAX_LEVEL", 5),
                "baseXp": getattr(db, "ENCHANT_BASE_XP", 50)},
            "/api/catalog/class-skills": lambda: {"ok": True,
                "skills": getattr(db, "CLASS_SKILLS", {})},
            "/api/catalog/avatar-classes": lambda: {"ok": True,
                "classes": getattr(db, "AVATAR_CLASSES", {})},
            "/api/buffs": lambda: {"ok": True, "buffs": db.get_all_active_buffs(uid)},
            "/api/profile/talents": lambda: {"ok": True, "talents": db.get_talent_state(uid)},
            "/api/dashboard/widgets": lambda: {"ok": True, "widgets": db.get_dashboard_widgets(uid)},
            "/api/dashboard/summary": lambda: _dashboard_summary(uid),
            "/api/profile/titles": lambda: {
                "ok": True,
                "selectedTitle": (db.get_user(uid) or {}).get("selected_title") or "",
                "titles": db.get_unlocked_titles(uid),
            },
            "/api/year-wrapped": lambda: {"ok": True, "wrapped": db.get_year_wrapped(uid)},
            # Parity SettingsPage: versi app + path DB (label database group)
            "/api/catalog/avatar-classes": lambda: {
                "ok": True,
                # Parity db.AVATAR_CLASSES — hero class select SettingsView
                "classes": [
                    {"key": k, "name": v.get("name") or k, "icon": v.get("icon") or "",
                     "bonus": v.get("bonus") or ""}
                    for k, v in (db.AVATAR_CLASSES or {}).items()
                ],
            },
            "/api/catalog/themes": lambda: {
                "ok": True,
                # Parity SettingsPage theme radios: (key, label, primary/glow utk preview dot)
                "themes": [
                    {"key": k, "label": v.get("label") or k,
                     "primary": v.get("primary") or "", "glow": v.get("glow") or ""}
                    for k, v in (db.THEMES or {}).items()
                ],
            },
            "/api/version": lambda: {
                "ok": True,
                "version": getattr(__import__("updater"), "APP_VERSION", "?"),
                "dbPath": getattr(db, "DB_PATH", ""),
            },
            "/api/leaderboard": lambda: {
                "ok": True,
                "linked": bool(db.get_cloud_user_link(uid)),
                "leaderboard": [
                    {
                        "id": str(r.get("id")),
                        "username": r.get("username") or "",
                        "displayName": r.get("display_name") or r.get("username") or "",
                        "level": int(r.get("level") or 1),
                        "xp": int(r.get("total_xp_earned") or 0),
                        "gold": int(r.get("gold") or 0),
                        "sportLevel": int(r.get("sport_level") or 1),
                        "pets": int(r.get("pet_count") or 0),
                        "rebirth": int(r.get("rebirth_count") or 0),
                        "title": _leaderboard_title_loc(r.get("selected_title") or "", uid),
                        # Parity LeaderboardPage: 💞 + tooltip partner / single
                        "partner": (db.get_couple_partners_map().get(r.get("id")) or [None, ""])[1],
                        "cloudUserId": r.get("cloud_user_id") or "",
                        "presence": (
                            (db.get_cached_presence(r.get("cloud_user_id")) or {}).get("status")
                            if r.get("cloud_user_id")
                            else "offline"
                        ),
                    }
                    for r in (db.get_leaderboard_for_user(uid) or db.get_leaderboard(50) or [])
                ],
            },
        }
        if path in routes:
            self._send(200, routes[path]())
            return
        if path == "/api/update/check":
            # Parity _check_for_update_manual: updater.check_for_update (best-effort).
            try:
                import updater
                info = updater.check_for_update()
                self._send(200, {"ok": True, "update": info or None,
                                 "latest": not bool(info),
                                 "version": getattr(updater, "APP_VERSION", "?")})
            except Exception as e:
                self._send(200, {"ok": True, "update": None, "latest": True,
                                 "error": str(e)})
            return
        if path == "/api/holidays":
            year = int((qs.get("year") or [0])[0] or 0) or None
            try:
                import holidays as hol
                from datetime import datetime as _dt
                y = year or _dt.now().year
                data = hol.get_holidays_for_year(y) or {}
            except Exception:
                data = {}
                y = year or 0
            items = []
            for ds, names in data.items():
                if isinstance(names, (list, tuple)) and len(names) >= 2:
                    nid, nen = names[0], names[1]
                else:
                    nid = nen = str(names)
                items.append({"date": ds, "nameId": nid, "nameEn": nen, "type": "national"})
            self._send(200, {"ok": True, "year": y, "holidays": items})
            return
        # Serve a Love Space photo image (BLOB) to the browser <img>. Visibility
        # (owner / shared-with-couple) is enforced inside get_love_space_photo.
        if path == "/api/love/photo/image":
            pid = (qs.get("id") or [None])[0]
            if not pid:
                self._send(400, {"ok": False, "error": "id"})
                return
            try:
                ph = db.get_love_space_photo(uid, int(pid))
            except (ValueError, TypeError):
                ph = None
            if not ph:
                self._send(404, {"ok": False, "error": "not_found"})
                return
            blob = ph.get("image_data")
            mime = (ph.get("mime_type") or "image/jpeg").split(";")[0].strip()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(blob)))
            self.send_header("Cache-Control", "private, max-age=3600")
            self.end_headers()
            self.wfile.write(blob)
            return

        if path == "/api/profile/photo":
            try:
                ph = db.get_profile_photo(uid)
            except Exception:
                ph = None
            if not ph or not ph.get("image_data"):
                self._send(404, {"ok": False, "error": "not_found"})
                return
            blob = ph["image_data"]
            mime = (ph.get("mime_type") or "image/jpeg").split(";")[0].strip()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(blob)))
            self.send_header("Cache-Control", "private, max-age=300")
            self.end_headers()
            self.wfile.write(blob)
            return

        extra = life_api.handle_get(path, uid, qs)
        if extra is not None:
            # Marker unduhan binary (parity ekspor PyQt): dict {"__file_bytes__": bytes}
            file_bytes = extra.get("__file_bytes__") if isinstance(extra, dict) else None
            if file_bytes is not None:
                fname = extra.get("name") or "export.bin"
                mime = extra.get("mime") or "application/octet-stream"
                self.send_response(200)
                self._cors()
                self.send_header("Content-Type", mime)
                self.send_header("Content-Disposition", f'attachment; filename="{fname.split("/")[-1]}"')
                self.send_header("Content-Length", str(len(file_bytes)))
                self.end_headers()
                self.wfile.write(file_bytes)
                return
            self._send(200, extra)
            return
        extra = studio_api.handle_get(path, uid, qs)
        if extra is not None:
            self._send(200, extra)
            return
        if path.startswith("/api/cloud"):
            try:
                import cloud_api
                extra = cloud_api.handle_get(path, uid)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            if extra is not None:
                code = 200 if extra.get("ok", True) else 400
                self._send(code, extra)
                return

        if path == "/api/tracker/export":
            try:
                data = db.export_tracker_data(uid)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, {"ok": True, "tracker": data})
            return
        if path == "/api/update/check":
            info = {"ok": True, "current": None, "update": None}
            try:
                import updater
                info["current"] = getattr(updater, "APP_VERSION", None)
                info["update"] = updater.check_for_update()
            except Exception as e:
                info["error"] = str(e)
            self._send(200, info)
            return

        if path == "/api/bootstrap":
            snap = _snapshot(uid)
            snap["ok"] = True
            snap["shop"] = _shop_catalog()
            snap["petCatalog"] = _pet_catalog()
            snap["bossCatalog"] = _boss_catalog()
            snap["recipes"] = _recipe_catalog()
            self._send(200, snap)
            return

        self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            body = {}

        if path == "/api/auth/reset":
            username = (body.get("username") or "").strip()
            code = (body.get("code") or "").strip()
            new_pw = body.get("password") or body.get("newPassword") or ""
            try:
                conn = db.get_conn()
                row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
                conn.close()
                if not row:
                    self._send(400, {"ok": False, "error": "user_not_found"})
                    return
                uid = int(row["id"])
                if not db.verify_backup_code(uid, code):
                    self._send(400, {"ok": False, "error": "invalid_code"})
                    return
                result = db.reset_password_with_backup_code(uid, new_pw)
                self._send(200, {"ok": True, "result": result if isinstance(result, dict) else {"ok": True}})
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
            return
        if path in ("/api/auth/login", "/api/auth/register"):
            try:
                if path.endswith("register"):
                    result = db.register_user(
                        body.get("username") or "",
                        body.get("password") or "",
                        display_name=body.get("displayName") or "",
                        bio=body.get("bio") or "",
                        avatar_class=body.get("avatarClass") or "warrior",
                    )
                    if result.get("ok"):
                        result = db.login_user(body.get("username") or "", body.get("password") or "")
                else:
                    result = db.login_user(body.get("username") or "", body.get("password") or "")
                if not result.get("ok"):
                    self._send(401, {"ok": False, "error": result.get("msg") or "login_failed", "result": result})
                    return
                user = result.get("user") or {}
                uid = int(user.get("id"))
                token = db.create_session_token(uid)
                configure(uid, token)
                self._send(200, {"ok": True, "token": token, "user": _row_user(db.get_user(uid))})
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
            return

        if path == "/api/profile/rebirth":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = db.perform_rebirth(uid)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True}))
            return
        if path == "/api/profile/title":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            key = str(body.get("key") or "")
            try:
                res = db.set_title(uid, key)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            if not res.get("ok"):
                self._send(400, {"ok": False, "error": "title_locked"})
                return
            self._send(200, _ok_payload(uid, res))
            return
        if path == "/api/profile/photo/remove":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            res = db.remove_profile_photo(uid, uid)
            if not res.get("ok"):
                self._send(400, {"ok": False, "error": res.get("code") or "failed"})
                return
            self._send(200, _ok_payload(uid, res))
            return
        if path == "/api/profile/redeem":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = db.redeem_code(uid, (body.get("code") or "").strip())
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True}))
            return
        if path == "/api/admin/debug":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            u = db.get_user(uid) or {}
            if not u.get("is_admin"):
                self._send(403, {"ok": False, "error": "not_admin"})
                return
            action = str(body.get("action") or "")
            amount = int(body.get("amount") or 0)
            result = None
            if action == "add_xp":
                result = db.gain_xp_gold(uid, amount, 0)
            elif action == "add_gold":
                result = db.gain_xp_gold(uid, 0, amount)
            elif action == "fill_hp_mp":
                db.update_user(uid, hp=u.get("max_hp"), mp=u.get("max_mp"))
                result = {"ok": True, "msg": db.tr_db(user_id=uid, key="debug_hp_mp_restored")}
            elif action == "max_level":
                target = 50
                cur = int(u.get("level") or 1)
                if cur >= target:
                    result = {"ok": True, "msg": db.tr_db(user_id=uid, key="debug_level_already", level=cur)}
                else:
                    need = sum(lvl * 150 for lvl in range(cur, target))
                    db.gain_xp_gold(uid, need, 0)
                    result = {"ok": True, "msg": db.tr_db(user_id=uid, key="debug_level_set", target=target)}
            elif action == "complete_tasks":
                for h in db.get_habits(uid) or []:
                    if not h.get("done_today"):
                        db.complete_habit(uid, h["id"], "up")
                for d in db.get_dailies(uid) or []:
                    if not d.get("done_today"):
                        db.complete_daily(uid, d["id"])
                for t in db.get_todos(uid) or []:
                    if not t.get("done"):
                        db.complete_todo(uid, t["id"])
                result = {"ok": True, "msg": db.tr_db(user_id=uid, key="debug_tasks_done")}
            elif action == "pet_level_up":
                result = db.admin_level_up_all_pets(uid)
            elif action == "pet_add_exp":
                result = db.admin_add_exp_all_pets(uid, max(1, amount))
            elif action == "pet_feed":
                result = db.admin_feed_all_pets(uid)
            else:
                result = {"ok": False, "msg": "unknown_action"}
            self._send(200, _ok_payload(uid, result))
            return
        if path == "/api/tracker/reset":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            pwd = body.get("password") or ""
            u = db.get_user(uid) or {}
            try:
                from database import _verify_password
                valid = _verify_password(pwd, u.get("password_hash", ""))
            except Exception:
                valid = db.login_user(u.get("username", ""), pwd).get("ok", False)
            if not valid:
                self._send(400, {"ok": False, "error": "wrong_password"})
                return
            try:
                db.reset_user_progress(uid)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, _ok_payload(uid, {"ok": True}))
            return
        if path == "/api/upload/file":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = _handle_upload_file(uid, body)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            if result.get("ok"):
                self._send(200, _ok_payload(uid, result))
            else:
                self._send(400, {"ok": False, "error": result.get("error") or "upload_failed", "result": result})
            return
        if path == "/api/profile/talent":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = db.unlock_talent(uid, body.get("key") or body.get("talentKey") or "")
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True}))
            return
        if path == "/api/dashboard/widgets":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            widgets = body.get("widgets")
            if not isinstance(widgets, list):
                self._send(400, {"ok": False, "error": "widgets_required"})
                return
            try:
                db.set_dashboard_widgets(uid, widgets)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, _ok_payload(uid, {"ok": True}))
            return
        if path == "/api/settings/backup":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            # Parity _manual_backup: db.backup_database() → path backup.
            try:
                bpath = db.backup_database()
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, _ok_payload(_state.get("user_id"),
                                        {"ok": bool(bpath), "path": bpath or ""}))
            return
        if path == "/api/profile/backup-codes":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = db.generate_backup_codes(uid)
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, {"ok": True, "result": result})
            return
        if path == "/api/profile/security":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = db.set_security_question(uid, body.get("question") or "", body.get("answer") or "")
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, {"ok": True, "result": result})
            return
        if path == "/api/profile/password":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                result = db.change_password(uid, body.get("oldPassword") or "", body.get("newPassword") or body.get("password") or "")
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, {"ok": True, "result": result})
            return
        if path == "/api/profile/lock":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            try:
                if body.get("unlock"):
                    result = db.unlock_account(uid, body.get("password") or "")
                else:
                    result = db.lock_account(uid, body.get("password") or "")
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, {"ok": True, "result": result})
            return
        if path == "/api/settings":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            lang = body.get("language") or body.get("lang")
            if lang in ("id", "en"):
                try:
                    db.set_user_language(uid, lang)
                except Exception:
                    pass
            theme = body.get("theme")
            if theme and hasattr(db, "set_user_theme"):
                try:
                    db.set_user_theme(uid, theme)
                except Exception:
                    pass
            kw = {}
            if body.get("displayName") or body.get("name"):
                kw["display_name"] = body.get("displayName") or body.get("name")
            if "bio" in body:
                kw["bio"] = body.get("bio") or ""
            if body.get("avatar") or body.get("avatarEmoji"):
                kw["avatar_emoji"] = body.get("avatar") or body.get("avatarEmoji")
            cls = body.get("heroClass") or body.get("avatarClass")
            if cls:
                kw["avatar_class"] = str(cls).lower()
            if kw:
                try:
                    db.update_user(uid, **kw)
                except Exception:
                    pass
            if "soundEnabled" in body:
                try:
                    db.set_user_settings(uid, sound_enabled=1 if body.get("soundEnabled") else 0)
                except Exception:
                    pass
            cur = body.get("currency")
            if cur:
                try:
                    db.set_user_currency(uid, str(cur).upper())
                except Exception:
                    pass
            if body.get("fontScale") is not None:
                try:
                    db.set_font_scale(uid, int(body.get("fontScale") or 100))
                except Exception:
                    pass
            if "highContrast" in body:
                try:
                    db.set_high_contrast(uid, bool(body.get("highContrast")))
                except Exception:
                    pass
            if body.get("avatarColor"):
                try:
                    db.update_user(uid, avatar_color=body.get("avatarColor"))
                except Exception:
                    pass
            if "onboardingDone" in body:
                try:
                    if body.get("onboardingDone"):
                        db.mark_onboarding_done(uid)
                except Exception:
                    pass
            self._send(200, _ok_payload(uid, {"ok": True, "user": _row_user(db.get_user(uid))}))
            return

        if path == "/api/tracker/import":
            if not _auth_ok(self):
                self._send(401, {"ok": False, "error": "unauthorized"})
                return
            uid = _state.get("user_id")
            payload = body.get("tracker") or body
            try:
                db.import_tracker_data(uid, payload, preserve_progress=bool(body.get("preserveProgress")))
            except Exception as e:
                self._send(400, {"ok": False, "error": str(e)})
                return
            self._send(200, _ok_payload(uid, {"ok": True}))
            return

        if path == "/api/update/check":
            info = {"ok": True, "current": None, "update": None}
            try:
                import updater
                info["current"] = getattr(updater, "APP_VERSION", None)
                chk = updater.check_for_update()
                info["update"] = chk
            except Exception as e:
                info["error"] = str(e)
            self._send(200, info)
            return

        if not _auth_ok(self):
            self._send(401, {"ok": False, "error": "unauthorized"})
            return
        uid = _state.get("user_id")
        parts = [p for p in path.split("/") if p]

        def fail(e):
            self._send(400, {"ok": False, "error": str(e)})

        try:
            # tasks reorder (drag & drop) — one call handles reorder-in-folder + move across folders
            if path == "/api/tasks/reorder":
                mode = str(body.get("mode") or "habit")
                items = body.get("items")
                if not isinstance(items, list):
                    self._send(400, {"ok": False, "error": "items_required"})
                    return
                result = db.reorder_tasks(uid, mode, items)
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "reorder_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/trash/restore":
                result = db.restore_task_from_trash(uid, body.get("trashId") or body.get("trash_id"))
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "restore_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return

            # habits
            if path == "/api/habits":
                name = (body.get("title") or body.get("name") or "").strip()
                if not name:
                    self._send(400, {"ok": False, "error": "empty"})
                    return
                db.add_habit(
                    uid, name,
                    icon=body.get("icon") or "⚔️",
                    difficulty=body.get("difficulty") or "medium",
                    positive=1 if body.get("isPositive", True) else 0,
                    negative=1 if body.get("isNegative") else 0,
                    notes=body.get("notes") or "",
                )
                fid = body.get("folderId") or body.get("folder_id")
                if fid not in (None, "", "null"):
                    try:
                        conn = db.get_conn()
                        row = conn.execute(
                            "SELECT id FROM habits WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)
                        ).fetchone()
                        conn.close()
                        if row:
                            db.update_habit(int(row["id"]), uid, folder_id=int(fid))
                    except Exception:
                        pass
                self._send(200, _ok_payload(uid))
                return
            if len(parts) >= 4 and parts[1] == "habits":
                hid = int(parts[2])
                action = parts[3]
                if action == "complete":
                    direction = "up" if body.get("positive", True) else "down"
                    result = db.complete_habit(uid, hid, direction=direction)
                    self._send(200, _ok_payload(uid, result))
                    return
                if action == "delete":
                    result = db.delete_habit(uid, hid)
                    self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True, "trash_id": None}))
                    return
                if action == "duplicate":
                    result = db.duplicate_habit(uid, hid)
                    self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {}))
                    return
                if action == "update":
                    kw = {}
                    if body.get("title") or body.get("name"):
                        kw["name"] = body.get("title") or body.get("name")
                    if body.get("difficulty"):
                        kw["difficulty"] = body.get("difficulty")
                    if body.get("icon"):
                        kw["icon"] = body.get("icon")
                    if "notes" in body:
                        kw["notes"] = body.get("notes") or ""
                    if "isPositive" in body:
                        kw["positive"] = 1 if body.get("isPositive") else 0
                    if "isNegative" in body:
                        kw["negative"] = 1 if body.get("isNegative") else 0
                    if "folderId" in body or "folder_id" in body:
                        fid = body.get("folderId") if "folderId" in body else body.get("folder_id")
                        kw["folder_id"] = int(fid) if fid not in (None, "", "null") else None
                    db.update_habit(hid, uid, **kw)
                    self._send(200, _ok_payload(uid))
                    return

            if path == "/api/dailies":
                name = (body.get("title") or body.get("name") or "").strip()
                if not name:
                    self._send(400, {"ok": False, "error": "empty"})
                    return
                days = body.get("repeatDays") or []
                repeat = _repeat_to_db(days)
                db.add_daily(
                    uid, name,
                    icon=body.get("icon") or "📅",
                    difficulty=body.get("difficulty") or "medium",
                    notes=body.get("notes") or "",
                    repeat_days=repeat,
                )
                fid = body.get("folderId") or body.get("folder_id")
                if fid not in (None, "", "null"):
                    try:
                        conn = db.get_conn()
                        row = conn.execute(
                            "SELECT id FROM dailies WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)
                        ).fetchone()
                        conn.close()
                        if row:
                            db.set_item_folder(uid, "daily", int(row["id"]), int(fid))
                    except Exception:
                        pass
                self._send(200, _ok_payload(uid))
                return
            if len(parts) >= 4 and parts[1] == "dailies":
                did = int(parts[2])
                action = parts[3]
                if action == "complete":
                    result = db.complete_daily(uid, did)
                    self._send(200, _ok_payload(uid, result))
                    return
                if action == "fail":
                    result = db.fail_daily(uid, did)
                    self._send(200, _ok_payload(uid, result))
                    return
                if action == "freeze":
                    result = db.add_freeze_to_daily(uid, did)
                    self._send(200, _ok_payload(uid, result))
                    return
                if action == "delete":
                    result = db.delete_daily(uid, did)
                    self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True, "trash_id": None}))
                    return
                if action == "duplicate":
                    result = db.duplicate_daily(uid, did)
                    self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {}))
                    return
                if action == "update":
                    kw = {}
                    if body.get("title") or body.get("name"):
                        kw["name"] = body.get("title") or body.get("name")
                    if body.get("difficulty"):
                        kw["difficulty"] = body.get("difficulty")
                    if "notes" in body:
                        kw["notes"] = body.get("notes") or ""
                    if body.get("repeatDays") is not None:
                        days = body.get("repeatDays") or []
                        kw["repeat_days"] = _repeat_to_db(days)
                    if "folderId" in body or "folder_id" in body:
                        fid = body.get("folderId") if "folderId" in body else body.get("folder_id")
                        kw["folder_id"] = int(fid) if fid not in (None, "", "null") else None
                    db.update_daily(did, uid, **kw)
                    self._send(200, _ok_payload(uid))
                    return

            if path == "/api/todos":
                name = (body.get("title") or body.get("name") or "").strip()
                if not name:
                    self._send(400, {"ok": False, "error": "empty"})
                    return
                db.add_todo(
                    uid, name,
                    priority=body.get("difficulty") or "medium",
                    icon=body.get("icon") or "📜",
                    due_date=body.get("dueDate"),
                    notes=body.get("notes") or "",
                )
                fid = body.get("folderId") or body.get("folder_id")
                if fid not in (None, "", "null"):
                    try:
                        conn = db.get_conn()
                        row = conn.execute(
                            "SELECT id FROM todos WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)
                        ).fetchone()
                        conn.close()
                        if row:
                            db.update_todo(int(row["id"]), uid, folder_id=int(fid))
                    except Exception:
                        pass
                self._send(200, _ok_payload(uid))
                return
            if len(parts) >= 4 and parts[1] == "todos":
                tid = int(parts[2])
                action = parts[3]
                if action == "complete":
                    result = db.complete_todo(uid, tid)
                    self._send(200, _ok_payload(uid, result))
                    return
                if action == "delete":
                    result = db.delete_todo(uid, tid)
                    self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True, "trash_id": None}))
                    return
                if action == "duplicate":
                    result = db.duplicate_todo(uid, tid)
                    self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {}))
                    return
                if action == "update":
                    kw = {}
                    if body.get("title") or body.get("name"):
                        kw["name"] = body.get("title") or body.get("name")
                    if body.get("difficulty") or body.get("priority"):
                        kw["priority"] = body.get("difficulty") or body.get("priority")
                    if body.get("icon"):
                        kw["icon"] = body.get("icon")
                    if "notes" in body:
                        kw["notes"] = body.get("notes") or ""
                    if "dueDate" in body:
                        kw["due_date"] = body.get("dueDate") or None
                    if "folderId" in body or "folder_id" in body:
                        fid = body.get("folderId") if "folderId" in body else body.get("folder_id")
                        kw["folder_id"] = int(fid) if fid not in (None, "", "null") else None
                    db.update_todo(tid, uid, **kw)
                    self._send(200, _ok_payload(uid))
                    return

            if path == "/api/shop/buy":
                item_id = body.get("itemId") or body.get("item_id")
                idem = str(body.get("idempotencyKey") or body.get("idempotency_key") or uuid.uuid4())
                qty = int(body.get("quantity") or 1)
                import cloud_api
                if cloud_api.is_shop_cloud(uid):
                    try:
                        result = cloud_api.shop_cloud_buy(uid, item_id, qty, idem)
                    except Exception as e:
                        self._send(400, {"ok": False, "error": str(e), **_snapshot(uid)})
                        return
                    self._send(200, _ok_payload(uid, result))
                    return
                result = db.buy_item(uid, item_id)
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "buy_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/shop/sell":
                item_id = body.get("itemId") or body.get("item_id")
                row_id = body.get("rowId")
                if not row_id:
                    for r in db.get_inventory(uid):
                        if r.get("item_id") == item_id:
                            row_id = r.get("id")
                            break
                result = db.sell_item(uid, row_id, quantity=int(body.get("quantity") or 1))
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/shop/use":
                result = db.use_item(uid, body.get("itemId") or body.get("item_id"))
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/shop/equip":
                item_id = body.get("itemId") or body.get("item_id")
                equipped = bool(body.get("equipped", True))
                import cloud_api
                if cloud_api.is_shop_cloud(uid):
                    try:
                        result = cloud_api.shop_cloud_equip(uid, item_id, equipped)
                    except Exception as e:
                        self._send(400, {"ok": False, "error": str(e), **_snapshot(uid)})
                        return
                    self._send(200, _ok_payload(uid, result))
                    return
                result = _equip_item(uid, item_id, equipped)
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "equip_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/shop/craft":
                rid = body.get("recipeId") or body.get("resultItemId")
                idem = str(body.get("idempotencyKey") or body.get("idempotency_key") or uuid.uuid4())
                import cloud_api
                if cloud_api.is_shop_cloud(uid):
                    try:
                        result = cloud_api.shop_cloud_craft(uid, rid, idem)
                    except Exception as e:
                        self._send(400, {"ok": False, "error": str(e), **_snapshot(uid)})
                        return
                    self._send(200, _ok_payload(uid, result))
                    return
                result = db.craft_item(uid, rid)
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "craft_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/shop/enchant":
                item_id = body.get("itemId") or body.get("item_id")
                idem = str(body.get("idempotencyKey") or body.get("idempotency_key") or uuid.uuid4())
                import cloud_api
                if cloud_api.is_shop_cloud(uid):
                    try:
                        result = cloud_api.shop_cloud_enchant(uid, item_id, idem)
                    except Exception as e:
                        self._send(400, {"ok": False, "error": str(e), **_snapshot(uid)})
                        return
                    self._send(200, _ok_payload(uid, result))
                    return
                result = db.enchant_item(uid, item_id)
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "enchant_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return

            if path == "/api/pets/adopt":
                result = db.adopt_pet(uid, body.get("petId"))
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/pets/feed":
                result = db.feed_pet(uid, body.get("petId"))
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/pets/train":
                result = db.train_pet(uid, body.get("petId"))
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/pets/equip":
                result = db.equip_pet(uid, body.get("petId"))
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/pets/unequip":
                result = db.unequip_pet(uid, body.get("petId"))
                self._send(200, _ok_payload(uid, result))
                return

            if path == "/api/boss/start":
                u = db.get_user(uid)
                gid = u.get("guild_id") or 0
                result = db.start_boss(gid, body.get("bossId"), u)
                self._send(200, _ok_payload(uid, result, extra={"activeBossId": body.get("bossId")}))
                return
            if path == "/api/boss/attack":
                u = db.get_user(uid)
                gid = u.get("guild_id") or 0
                action = body.get("action") or "light"
                result = db.attack_boss(uid, gid, action=action)
                self._send(200, _ok_payload(uid, result))
                return
            if path == "/api/boss/flee":
                self._send(200, _ok_payload(uid, {"ok": True, "fled": True}))
                return
            if path == "/api/skill/use":
                result = db.use_class_skill(uid)
                if not result.get("ok"):
                    self._send(400, {"ok": False, "error": result.get("msg") or "skill_failed", **_snapshot(uid)})
                    return
                self._send(200, _ok_payload(uid, result))
                return

            if len(parts) >= 4 and parts[1] == "achievements" and parts[3] == "claim":
                aid = parts[2]
                try:
                    aid_int = int(aid)
                except ValueError:
                    aid_int = aid
                result = db.claim_achievement_reward(uid, aid_int)
                self._send(200, _ok_payload(uid, result))
                return

            life = life_api.handle_post(path, uid, body, parts)
            if life is not None:
                if life.get("skip_snap"):
                    self._send(200, {"ok": True, "result": life.get("result")})
                    return
                self._send(200, _ok_payload(uid, life.get("result")))
                return
            studio = studio_api.handle_post(path, uid, body, parts)
            if studio is not None:
                if studio.get("skip_snap"):
                    payload = {"ok": True, "result": studio.get("result")}
                    if isinstance(studio.get("result"), dict):
                        payload.update(studio.get("result"))
                    self._send(200, payload)
                    return
                self._send(200, _ok_payload(uid, studio.get("result")))
                return
            if path == "/api/admin/debug":
                u = db.get_user(uid) or {}
                if not u.get("is_admin"):
                    self._send(403, {"ok": False, "error": "forbidden"})
                    return
                action = body.get("action") or ""
                result = {"ok": True}
                if action == "xp":
                    result = db.gain_xp_gold(uid, int(body.get("amount") or 0), 0)
                elif action == "gold":
                    result = db.gain_xp_gold(uid, 0, int(body.get("amount") or 0))
                elif action == "fill":
                    db.update_user(uid, hp=u.get("max_hp"), mp=u.get("max_mp"))
                elif action == "maxLevel":
                    target = 50
                    needed = 0
                    for lvl in range(int(u.get("level") or 1), target):
                        needed += lvl * 150
                    result = db.gain_xp_gold(uid, needed, 0)
                elif action == "completeTasks":
                    for h in db.get_habits(uid):
                        if not h.get("done_today"):
                            db.complete_habit(uid, h["id"], "up")
                    for d in db.get_dailies(uid):
                        if not d.get("done_today"):
                            db.complete_daily(uid, d["id"])
                    for t in db.get_todos(uid):
                        if not t.get("done"):
                            db.complete_todo(uid, t["id"])
                elif action == "petLevel":
                    result = db.admin_level_up_all_pets(uid)
                elif action == "petExp":
                    result = db.admin_add_exp_all_pets(uid, int(body.get("amount") or 100)) if hasattr(db, "admin_add_exp_all_pets") else {"ok": False}
                elif action == "feedPets":
                    result = db.admin_feed_all_pets(uid) if hasattr(db, "admin_feed_all_pets") else {"ok": False}
                self._send(200, _ok_payload(uid, result if isinstance(result, dict) else {"ok": True}))
                return
            if path.startswith("/api/cloud"):
                import cloud_api
                extra = cloud_api.handle_post(path, uid, body)
                if extra is not None:
                    code = 200 if extra.get("ok", True) else 400
                    self._send(code, extra)
                    return
        except Exception as e:
            fail(e)
            return

        self._send(404, {"ok": False, "error": "not_found"})

    def _serve_audio(self, file_path: str):
        """Serve a local audio file with HTTP Range support (for <audio> seek).

        Only files inside the CraftLife Music library dir are reachable; nothing
        is uploaded/streamed over the internet beyond the local loopback.
        """
        import mimetypes
        from http import HTTPStatus
        try:
            import music_downloader as md
            lib_dir = os.path.realpath(md.get_download_dir())
        except Exception:
            self._send(404, {"ok": False, "error": "no_music_dir"})
            return
        if not file_path:
            self._send(404, {"ok": False, "error": "bad_path"})
            return
        real = os.path.realpath(file_path)
        if not real.startswith(lib_dir + os.sep):
            self._send(403, {"ok": False, "error": "forbidden"})
            return
        if not os.path.isfile(real):
            self._send(404, {"ok": False, "error": "not_found"})
            return
        size = os.path.getsize(real)
        ctype = mimetypes.guess_type(real)[0] or "audio/mpeg"
        rng = self.headers.get("Range")
        start = 0
        end = size - 1
        if rng:
            try:
                spec = rng.replace("bytes=", "").strip()
                if "-" in spec:
                    a, b = spec.split("-", 1)
                    start = int(a) if a else 0
                    end = (int(b) if b else end)
                else:
                    start = int(spec)
            except (ValueError, IndexError):
                start = 0
                end = size - 1
            start = max(0, min(start, size - 1))
            end = max(start, min(end, size - 1))
        length = end - start + 1
        self.send_response(206 if rng else 200)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        try:
            with open(real, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _serve_static(self, path: str):
        try:
            from web_shell import web_dist_candidates
            cands = web_dist_candidates()
        except Exception:
            here = os.path.dirname(os.path.abspath(__file__))
            cands = [
                os.path.join(here, "web", "dist"),
                os.path.join(os.path.dirname(here), "web", "dist"),
            ]
            meipass = getattr(__import__("sys"), "_MEIPASS", None)
            if meipass:
                cands.insert(0, os.path.join(meipass, "web", "dist"))
        root = next((c for c in cands if os.path.isdir(c)), cands[-1])
        if not os.path.isdir(root) or not os.path.isfile(os.path.join(root, "index.html")):
            html = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'><title>CraftLife</title></head>"
                "<body style='font-family:Segoe UI,sans-serif;background:#0f172a;color:#e2e8f0;padding:48px'>"
                "<h1>UI React belum di-build</h1>"
                "<p>Folder <code>web/dist</code> kosong. API di port ini hidup, tapi tidak ada index.html.</p>"
                "<ol>"
                "<li>Buka PowerShell di folder <code>web</code></li>"
                "<li><code>npm install</code></li>"
                "<li><code>npm run build</code></li>"
                "<li>Jalankan ulang CraftLife</li>"
                "</ol>"
                "<p>Jangan pakai <code>npm run dev</code> untuk jendela exe — WebEngine memuat "
                "<code>http://127.0.0.1:8765/</code>.</p>"
                "</body></html>"
            ).encode("utf-8")
            self._send(200, html, "text/html")
            return
        if path in ("/", "", "/index.html"):
            rel = "index.html"
        else:
            rel = path.lstrip("/")
        full = os.path.normpath(os.path.join(root, rel))
        if not full.startswith(os.path.normpath(root)):
            self._send(403, {"ok": False})
            return
        if not os.path.isfile(full):
            full = os.path.join(root, "index.html")
        lower = full.lower()
        ctype = "text/html"
        if lower.endswith(".js") or lower.endswith(".mjs"):
            ctype = "application/javascript"
        elif lower.endswith(".css"):
            ctype = "text/css"
        elif lower.endswith(".ico"):
            ctype = "image/x-icon"
        elif lower.endswith(".png"):
            ctype = "image/png"
        elif lower.endswith(".jpg") or lower.endswith(".jpeg"):
            ctype = "image/jpeg"
        elif lower.endswith(".webp"):
            ctype = "image/webp"
        elif lower.endswith(".svg"):
            ctype = "image/svg+xml"
        elif lower.endswith(".woff"):
            ctype = "font/woff"
        elif lower.endswith(".woff2"):
            ctype = "font/woff2"
        elif lower.endswith(".json"):
            ctype = "application/json"
        elif lower.endswith(".map"):
            ctype = "application/json"
        with open(full, "rb") as f:
            data = f.read()
        self._send(200, data, ctype)


_httpd = None


def start_server(host="127.0.0.1", port=8765):
    global _httpd
    if _httpd is not None:
        return _httpd, f"http://{host}:{port}"
    last_err = None
    for candidate in range(int(port), int(port) + 8):
        try:
            httpd = ThreadingHTTPServer((host, candidate), Handler)
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            _httpd = httpd
            if candidate != int(port):
                os.environ["CRAFTLIFE_API_PORT"] = str(candidate)
            print(f"CraftLife API http://{host}:{candidate}", flush=True)
            return httpd, f"http://{host}:{candidate}"
        except OSError as exc:
            last_err = exc
            continue
    print(f"CraftLife API gagal bind {host}:{port}: {last_err}", flush=True)
    raise last_err or OSError("api_bind_failed")


if __name__ == "__main__":
    db.init_db()
    _ensure_user()
    host = os.environ.get("CRAFTLIFE_API_HOST", "127.0.0.1")
    port = int(os.environ.get("CRAFTLIFE_API_PORT", "8765"))
    start_server(host, port)
    print(f"CraftLife API http://{host}:{port} user_id={_state.get('user_id')}", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
