import React from 'react';
import { Link } from 'react-router-dom';
import './HomePage.css';

const categories = [
    {
        name: 'AI-Powered Learning & Study Tools',
        tools: [
            { name: 'AI Summarizer', path: '/ai_summarizer' },
            { name: 'AI Quiz Creator', path: '/quiz_creator' },
            { name: 'AI Segmenter', path: '/ai_segmenter' },
            { name: 'AI Chronology', path: '/ai_chrono' },
            { name: 'AI Story Visualizer', path: '/ai_story_visualizer' },
            { name: 'AI Topic Modeller', path: '/ai_topic_modeller' },
            { name: 'AI Translator', path: '/ai_translator' },
            { name: 'AI Transcription', path: '/ai_transcription' },
            { name: 'AI Image Talker', path: '/ai_image_talker' },
            { name: 'AI Infographic Maker', path: '/ai_infographic_maker' },
            { name: 'AI Digital Debater', path: '/ai_digital_debate' },
            { name: 'AI Homework Helper', path: '/ai_homework_helper' },
            { name: 'AI Chronology Tool', path: '/ai_chronology_tool' },
            { name: 'Mindful Study Planner', path: '/mindful_study_planner' },
            { name: 'Sentence Simplifier', path: '/sentence_simplifier' },
            { name: 'AI Lesson Plan Designer', path: '/ai_lesson_plan_designer' },
            { name: 'Customizable Flashcard Generator', path: '/customizable_flashcard_generator' },
            { name: 'Language Learning Games', path: '/language_learning_games' },
            { name: 'Virtual Language Coach', path: '/virtual_language_coach' },
            { name: 'Interactive Timeline Explorer', path: '/interactive_timeline_explorer' },
            { name: 'Collaborative Mind Mapping', path: '/collaborative_mind_mapping' },
            { name: 'Ethical AI Tour', path: '/ethical_ai_tour' },
            { name: 'AI-Powered Test Prep', path: '/ai_powered_test_prep' },
            { name: 'Mood-Based Study Music Generator', path: '/mood_based_study_music_generator' },
            { name: 'Adaptive Learning Quiz Maker', path: '/adaptive_learning_quiz_maker' },
            { name: 'Speed Reading AI', path: '/speed_reading_ai' },
            { name: 'Historical Document Analyzer', path: '/historical_document_analyzer' },
            { name: 'AI STEM Challenge Generator', path: '/ai_stem_challenge_generator' },
            { name: 'Debate & Argument Structurer', path: '/debate_argument_structurer' },
            { name: 'Study Habit Tracker AI', path: '/study_habit_tracker_ai' },
            { name: 'Virtual Flashcard Study Bot', path: '/virtual_flashcard_study_bot' },
            { name: 'Smart Knowledge Vault', path: '/smart_knowledge_vault' },
        ],
    },
    {
        name: 'AI-Powered Writing & Creativity Tools',
        tools: [
            { name: 'Creative Writing Prompts Generator', path: '/creative_writing_prompts_generator' },
            { name: 'AI Story Generator', path: '/ai_story_generator' },
            { name: 'AI Poem Generator', path: '/ai_poem_generator' },
            { name: 'AI Essay Outliner', path: '/ai_essay_outliner' },
            { name: 'AI-Powered Grammar & Style Checker', path: '/ai_grammar_style_checker' },
            { name: 'Academic Citation Generator', path: '/academic_citation_generator' },
            { name: 'Paraphrasing AI', path: '/paraphrasing_ai' },
            { name: 'AI Comedy & Joke Generator', path: '/ai_comedy_joke_generator' },
            { name: 'Plot Generator for Writers', path: '/plot_generator_for_writers' },
            { name: 'AI Comic Strip Creator', path: '/ai_comic_strip_creator' },
            { name: 'Story-to-Comics Converter', path: '/story_to_comics_converter' },
            { name: 'Storyboard AI Creator', path: '/storyboard_ai_creator' },
            { name: 'AI-Powered Metaphor Generator', path: '/ai_metaphor_generator' },
            { name: 'AI Fairytale Maker', path: '/ai_fairytale_maker' },
            { name: 'Interactive Fiction AI', path: '/interactive_fiction_ai' },
            { name: 'Character & Dialogue Generator', path: '/character_dialogue_generator' },
            { name: 'Novel-Writing AI Companion', path: '/novel_writing_ai_companion' },
        ],
    },
    {
        name: 'AI-Powered Visual & Multimedia Tools',
        tools: [
            { name: '3D Model Builder', path: '/3d_model_builder' },
            { name: 'AI Art Creator for Kids', path: '/ai_art_creator_for_kids' },
            { name: 'AI Image Enhancer', path: '/ai_image_enhancer' },
            { name: 'Digital Portrait Creator', path: '/digital_portrait_creator' },
            { name: 'Virtual Science Lab', path: '/virtual_science_lab' },
            { name: 'Interactive Infographic Generator', path: '/interactive_infographic_generator' },
            { name: 'Data Story Builder', path: '/data_story_builder' },
            { name: 'AI-Powered Doodling App', path: '/ai_powered_doodling_app' },
            { name: 'Visual Study Guide Maker', path: '/visual_study_guide_maker' },
            { name: 'Learn by Drawing AI', path: '/learn_by_drawing_ai' },
            { name: 'AI-Generated Flashcard Illustrations', path: '/ai_generated_flashcard_illustrations' },
            { name: 'AI-Powered Whiteboard Explainer', path: '/ai_powered_whiteboard_explainer' },
            { name: 'AI-Generated Map Builder', path: '/ai_generated_map_builder' },
            { name: 'Science Diagram AI Generator', path: '/science_diagram_ai_generator' },
            { name: 'Interactive Science Visualizer', path: '/interactive_science_visualizer' },
            { name: 'Artistic Style Transfer AI', path: '/artistic_style_transfer_ai' },
            { name: 'AI-Powered Digital Poster Maker', path: '/ai_powered_digital_poster_maker' },
            { name: 'Auto Colorization Tool for Learning', path: '/auto_colorization_tool_for_learning' },
        ],
    },
    {
        name: 'AI-Powered Audio & Speech Tools',
        tools: [
            { name: 'AI Voice Cloning', path: '/ai_voice_cloning' },
            { name: 'AI Dubbing & Speaker Diarization', path: '/ai_dubbing_speaker_diarization' },
            { name: 'Lip Sync on Videos AI', path: '/lip_sync_on_videos_ai' },
            { name: 'AI Music Generator for Study', path: '/ai_music_generator_for_study' },
            { name: 'AI Speech-To-Text Converter', path: '/ai_speech_to_text_converter' },
            { name: 'AI-Powered Podcast Creator', path: '/ai_powered_podcast_creator' },
            { name: 'AI-Powered Language Pronunciation Coach', path: '/ai_powered_language_pronunciation_coach' },
            { name: 'Sound-Based Learning Assistant', path: '/sound_based_learning_assistant' },
            { name: 'Interactive AI Narrator', path: '/interactive_ai_narrator' },
            { name: 'AI Language Accent Neutralizer', path: '/ai_language_accent_neutralizer' },
            { name: 'AI-Powered Audiobook Narrator', path: '/ai_powered_audiobook_narrator' },
            { name: 'Text-to-Speech AI for Kids', path: '/text_to_speech_ai_for_kids' },
            { name: 'AI Interview Question Reader', path: '/ai_interview_question_reader' },
            { name: 'Interactive Audio Story Creator', path: '/interactive_audio_story_creator' },
            { name: 'AI-Generated Sound Effects Lab', path: '/ai_generated_sound_effects_lab' },
            { name: 'AI Voice Modulation Trainer', path: '/ai_voice_modulation_trainer' },
            { name: 'AI Singing Coach', path: '/ai_singing_coach' },
        ],
    },
    {
        name: 'AI-Powered Math & Science Tools',
        tools: [
            { name: 'AI Math Problem Visualizer', path: '/ai_math_problem_visualizer' },
            { name: 'AI Formula Explorer', path: '/ai_formula_explorer' },
            { name: 'AI Equation Balancer', path: '/ai_equation_balancer' },
            { name: 'Virtual Science Lab Assistant', path: '/virtual_science_lab_assistant' },
            { name: 'Interactive Physics Simulator', path: '/interactive_physics_simulator' },
            { name: 'Chemistry Reaction AI Visualizer', path: '/chemistry_reaction_ai_visualizer' },
            { name: 'AI Circuit Diagram Helper', path: '/ai_circuit_diagram_helper' },
            { name: 'AI-Based Graph Plotter', path: '/ai_based_graph_plotter' },
            { name: 'AI 3D Geometry Explorer', path: '/ai_3d_geometry_explorer' },
            { name: 'AI-Powered Statistics Helper', path: '/ai_powered_statistics_helper' },
            { name: 'AI Chemistry Periodic Table Guide', path: '/ai_chemistry_periodic_table_guide' },
            { name: 'AI-Based Algebra Assistant', path: '/ai_based_algebra_assistant' },
            { name: 'AI Astrophysics Learning Tool', path: '/ai_astrophysics_learning_tool' },
            { name: 'Biology Anatomy AI Explorer', path: '/biology_anatomy_ai_explorer' },
            { name: 'AI Climate Change Simulator', path: '/ai_climate_change_simulator' },
            { name: 'AI-Powered Genetics Tutor', path: '/ai_powered_genetics_tutor' },
            { name: 'AI Quantum Mechanics Explainer', path: '/ai_quantum_mechanics_explainer' },
            { name: 'AI Environmental Impact Calculator', path: '/ai_environmental_impact_calculator' },
        ],
    },
    {
        name: 'AI-Powered Productivity & Research Tools',
        tools: [
            { name: 'AI-Powered Note-Taking Assistant', path: '/ai_powered_note_taking_assistant' },
            { name: 'Smart Document Summarizer', path: '/smart_document_summarizer' },
            { name: 'AI-Based Citation Finder', path: '/ai_based_citation_finder' },
            { name: 'AI-Powered Presentation Builder', path: '/ai_powered_presentation_builder' },
            { name: 'AI-Based Task Manager', path: '/ai_based_task_manager' },
            { name: 'Automated Mind Mapping AI', path: '/automated_mind_mapping_ai' },
            { name: 'AI-Powered Smart Calendar', path: '/ai_powered_smart_calendar' },
            { name: 'Research Paper Categorization AI', path: '/research_paper_categorization_ai' },
            { name: 'AI-Based Time Management Assistant', path: '/ai_based_time_management_assistant' },
            { name: 'Smart Study Reminder AI', path: '/smart_study_reminder_ai' },
            { name: 'AI-Powered Habit Tracker', path: '/ai_powered_habit_tracker' },
            { name: 'AI-Powered Resume Analyzer', path: '/ai_powered_resume_analyzer' },
            { name: 'AI-Based Virtual Study Buddy', path: '/ai_based_virtual_study_buddy' },
            { name: 'AI-Powered Reading List Generator', path: '/ai_powered_reading_list_generator' },
            { name: 'AI-Based Smart Email Summarizer', path: '/ai_based_smart_email_summarizer' },
            { name: 'AI-Powered Document Comparison Tool', path: '/ai_powered_document_comparison_tool' },
            { name: 'AI Automated Bibliography Generator', path: '/ai_automated_bibliography_generator' },
        ],
    },
    {
        name: 'AI-Powered Games & Interactive Learning',
        tools: [
            { name: 'AI Puzzle Generator', path: '/ai_puzzle_generator' },
            { name: 'AI Trivia & Quiz Generator', path: '/ai_trivia_quiz_generator' },
            { name: 'AI Brain Training Games', path: '/ai_brain_training_games' },
            { name: 'AI-Powered Coding Playground', path: '/ai_powered_coding_playground' },
            { name: 'Interactive AI-Based Language Learning Game', path: '/interactive_ai_based_language_learning_game' },
            { name: 'AI-Based Historical Timeline Explorer', path: '/ai_based_historical_timeline_explorer' },
            { name: 'Virtual Escape Room AI', path: '/virtual_escape_room_ai' },
            { name: 'Interactive Geography Explorer', path: '/interactive_geography_explorer' },
            { name: 'AI-Based Science Fiction Adventure Game', path: '/ai_based_science_fiction_adventure_game' },
            { name: 'AI-Powered Puzzle Solving Assistant', path: '/ai_powered_puzzle_solving_assistant' },
            { name: 'AI-Generated Crossword Maker', path: '/ai_generated_crossword_maker' },
            { name: 'AI-Powered Learning RPG Game', path: '/ai_powered_learning_rpg_game' },
            { name: 'AI Adaptive Spelling Bee Game', path: '/ai_adaptive_spelling_bee_game' },
            { name: 'AI-Generated Language Flashcards Game', path: '/ai_generated_language_flashcards_game' },
            { name: 'AI Math Puzzle Generator', path: '/ai_math_puzzle_generator' },
            { name: 'AI Visual Riddle Solver', path: '/ai_visual_riddle_solver' },
            { name: 'AI-Powered History Detective Game', path: '/ai_powered_history_detective_game' },
            { name: 'AI-Based Financial Literacy Game', path: '/ai_based_financial_literacy_game' },
        ],
    },
    {
        name: 'AI-Powered Coding & Tech Education',
        tools: [
            { name: 'AI Code Playground for Kids', path: '/ai_code_playground_for_kids' },
            { name: 'AI-Powered Algorithm Trainer', path: '/ai_powered_algorithm_trainer' },
            { name: 'AI-Based Python Tutor', path: '/ai_based_python_tutor' },
            { name: 'AI Code Autocompletion for Beginners', path: '/ai_code_autocompletion_for_beginners' },
            { name: 'AI-Powered Debugging Assistant', path: '/ai_powered_debugging_assistant' },
            { name: 'AI-Based Web Development Tutor', path: '/ai_based_web_development_tutor' },
            { name: 'AI Coding Challenge Generator', path: '/ai_coding_challenge_generator' },
            { name: 'AI Algorithm Visualizer', path: '/ai_algorithm_visualizer' },
            { name: 'AI-Powered Game Development Assistant', path: '/ai_powered_game_development_assistant' },
            { name: 'AI-Powered Block-Based Coding Game', path: '/ai_powered_block_based_coding_game' },
            { name: 'AI Code Explanation Tool', path: '/ai_code_explanation_tool' },
            { name: 'AI-Powered Cybersecurity Basics Trainer', path: '/ai_powered_cybersecurity_basics_trainer' },
            { name: 'AI-Powered IT Certification Prep', path: '/ai_powered_it_certification_prep' },
            { name: 'AI Ethical Hacking Simulator', path: '/ai_ethical_hacking_simulator' },
            { name: 'AI-Based IoT Learning Platform', path: '/ai_based_iot_learning_platform' },
            { name: 'AI-Based Software Development Assistant', path: '/ai_based_software_development_assistant' },
            { name: 'AI Programming Flashcards', path: '/ai_programming_flashcards' },
            { name: 'AI-Powered DevOps Learning Assistant', path: '/ai_powered_devops_learning_assistant' },
            { name: 'AI-Based Data Science Learning Assistant', path: '/ai_based_data_science_learning_assistant' },
        ],
    },
    {
        name: 'AI-Powered Miscellaneous Tools',
        tools: [
            { name: 'AI Personal Finance Coach', path: '/ai_personal_finance_coach' },
            { name: 'AI Social Media Post Generator', path: '/ai_social_media_post_generator' },
            { name: 'AI-Based Public Speaking Coach', path: '/ai_based_public_speaking_coach' },
            { name: 'AI-Based Journalism Assistant', path: '/ai_based_journalism_assistant' },
            { name: 'AI Fake News Detector', path: '/ai_fake_news_detector' },
            { name: 'AI-Based Political Analysis Tool', path: '/ai_based_political_analysis_tool' },
            { name: 'AI-Based Job Interview Simulator', path: '/ai_based_job_interview_simulator' },
            { name: 'AI-Based Resume & Cover Letter Writer', path: '/ai_based_resume_cover_letter_writer' },
            { name: 'AI-Based Career Advisor', path: '/ai_based_career_advisor' },
            { name: 'AI-Based Goal Setting & Tracking', path: '/ai_based_goal_setting_tracking' },
            { name: 'AI Emotional Intelligence Coach', path: '/ai_emotional_intelligence_coach' },
            { name: 'AI-Based Productivity Booster', path: '/ai_based_productivity_booster' },
            { name: 'AI Digital Marketing Assistant', path: '/ai_digital_marketing_assistant' },
            { name: 'AI-Based Travel Guide & Planner', path: '/ai_based_travel_guide_planner' },
            { name: 'AI-Based History Fact Checker', path: '/ai_based_history_fact_checker' },
            { name: 'AI Legal Document Summarizer', path: '/ai_legal_document_summarizer' },
            { name: 'AI-Based Digital Ethics Advisor', path: '/ai_based_digital_ethics_advisor' },
            { name: 'AI-Based Content Repurposing Tool', path: '/ai_based_content_repurposing_tool' },
            { name: 'AI-Based Book Recommendation Engine', path: '/ai_based_book_recommendation_engine' },
            { name: 'AI-Based Public Policy Analyzer', path: '/ai_based_public_policy_analyzer' },
            { name: 'AI-Based Event Planner', path: '/ai_based_event_planner' },
            { name: 'AI Personalized Coaching Assistant', path: '/ai_personalized_coaching_assistant' },
            { name: 'AI-Based TED Talk Generator', path: '/ai_based_ted_talk_generator' },
            { name: 'AI-Based Food Nutrition Guide', path: '/ai_based_food_nutrition_guide' },
            { name: 'AI-Based Music Creation Platform', path: '/ai_based_music_creation_platform' },
            { name: 'AI-Based Poetry Analyzer', path: '/ai_based_poetry_analyzer' },
            { name: 'AI-Based Creative Thinking Assistant', path: '/ai_based_creative_thinking_assistant' },
            { name: 'AI-Based Museum Guide', path: '/ai_based_museum_guide' },
            { name: 'AI-Based Business Idea Generator', path: '/ai_based_business_idea_generator' },
            { name: 'AI-Based Smart Parenting Coach', path: '/ai_based_smart_parenting_coach' },
        ],
    },
    {
        name: 'Music AI Tools',
        tools: [
            { name: 'AI Emotion-Based Music Generator', path: '/ai_emotion_based_music_generator' },
            { name: 'AI Reverse Composer', path: '/ai_reverse_composer' },
            { name: 'AI Music History Explorer', path: '/ai_music_history_explorer' },
            { name: 'AI Adaptive Concert Simulator', path: '/ai_adaptive_concert_simulator' },
            { name: 'AI Personalized Instrument Teacher', path: '/ai_personalized_instrument_teacher' },
            { name: 'AI Genre Fusion Composer', path: '/ai_genre_fusion_composer' },
            { name: 'AI Soundscape Generator', path: '/ai_soundscape_generator' },
            { name: 'AI Lost Music Restoration', path: '/ai_lost_music_restoration' },
            { name: 'AI Lyric Emotion Enhancer', path: '/ai_lyric_emotion_enhancer' },
            { name: 'AI Ambient Noise Mixer', path: '/ai_ambient_noise_mixer' },
        ],
    },
    {
        name: 'Medical AI Tools',
        tools: [
            { name: 'AI Dream Pattern Analyzer', path: '/ai_dream_pattern_analyzer' },
            { name: 'AI Gut Health Optimizer', path: '/ai_gut_health_optimizer' },
            { name: 'AI Skin Aging Predictor', path: '/ai_skin_aging_predictor' },
            { name: 'AI Medical History Visualizer', path: '/ai_medical_history_visualizer' },
            { name: 'AI Precision Medicine Generator', path: '/ai_precision_medicine_generator' },
            { name: 'AI Auto-Diagnosis Microscope', path: '/ai_auto_diagnosis_microscope' },
            { name: 'AI Blood Test Interpreter', path: '/ai_blood_test_interpreter' },
            { name: 'AI Emergency Response Guide', path: '/ai_emergency_response_guide' },
            { name: 'AI Surgical Recovery Predictor', path: '/ai_surgical_recovery_predictor' },
            { name: 'AI Virtual Organ Explorer', path: '/ai_virtual_organ_explorer' },
        ],
    },
    {
        name: 'Fitness & Sports AI Tools',
        tools: [
            { name: 'AI Personalized Workout Planner', path: '/ai_personalized_workout_planner' },
            { name: 'AI Injury Risk Predictor', path: '/ai_injury_risk_predictor' },
            { name: 'AI Sports Play Analyzer', path: '/ai_sports_play_analyzer' },
            { name: 'AI Adaptive Yoga Coach', path: '/ai_adaptive_yoga_coach' },
            { name: 'AI Virtual Running Partner', path: '/ai_virtual_running_partner' },
            { name: 'AI Custom Sneaker Designer', path: '/ai_custom_sneaker_designer' },
            { name: 'AI Sports Reaction Trainer', path: '/ai_sports_reaction_trainer' },
            { name: 'AI Smart Hydration Monitor', path: '/ai_smart_hydration_monitor' },
            { name: 'AI Biomechanics Optimizer', path: '/ai_biomechanics_optimizer' },
            { name: 'AI Adaptive Team Tactics Coach', path: '/ai_adaptive_team_tactics_coach' },
        ],
    },
    {
        name: 'Fashion & Beauty AI Tools',
        tools: [
            { name: 'AI Smart Wardrobe Organizer', path: '/ai_smart_wardrobe_organizer' },
            { name: 'AI Personal Stylist Chatbot', path: '/ai_personal_stylist_chatbot' },
            { name: 'AI Virtual Makeup Try-On', path: '/ai_virtual_makeup_try_on' },
            { name: 'AI Ethical Fashion Finder', path: '/ai_ethical_fashion_finder' },
            { name: 'AI Clothing Fit Predictor', path: '/ai_clothing_fit_predictor' },
            { name: 'AI Perfume Personality Matcher', path: '/ai_perfume_personality_matcher' },
            { name: 'AI Hair Color & Style Simulator', path: '/ai_hair_color_style_simulator' },
            { name: 'AI Textile Pattern Generator', path: '/ai_textile_pattern_generator' },
            { name: 'AI Fashion Trend Forecaster', path: '/ai_fashion_trend_forecaster' },
            { name: 'AI Skin Undertone Analyzer', path: '/ai_skin_undertone_analyzer' },
        ],
    },
    {
        name: 'Space & Astronomy AI Tools',
        tools: [
            { name: 'AI Stargazing Assistant', path: '/ai_stargazing_assistant' },
            { name: 'AI Exoplanet Habitability Checker', path: '/ai_exoplanet_habitability_checker' },
            { name: 'AI Space Travel Planner', path: '/ai_space_travel_planner' },
            { name: 'AI Black Hole Visualizer', path: '/ai_black_hole_visualizer' },
            { name: 'AI Real-Time Meteor Tracker', path: '/ai_real_time_meteor_tracker' },
            { name: 'AI Cosmic Radiation Predictor', path: '/ai_cosmic_radiation_predictor' },
            { name: 'AI Dark Matter Explorer', path: '/ai_dark_matter_explorer' },
            { name: 'AI Mars Colony Simulator', path: '/ai_mars_colony_simulator' },
            { name: 'AI Alien Signal Analyzer', path: '/ai_alien_signal_analyzer' },
            { name: 'AI Personalized Horoscope Generator', path: '/ai_personalized_horoscope_generator' },
        ],
    },
    {
        name: 'Food & Cooking AI Tools',
        tools: [
            { name: 'AI Smart Recipe Generator', path: '/ai_smart_recipe_generator' },
            { name: 'AI Global Cuisine Explorer', path: '/ai_global_cuisine_explorer' },
            { name: 'AI Allergy-Free Meal Planner', path: '/ai_allergy_free_meal_planner' },
            { name: 'AI Zero-Waste Cooking Assistant', path: '/ai_zero_waste_cooking_assistant' },
            { name: 'AI Fermentation Guide', path: '/ai_fermentation_guide' },
            { name: 'AI Spice Pairing Expert', path: '/ai_spice_pairing_expert' },
            { name: 'AI Smart Coffee Brewer', path: '/ai_smart_coffee_brewer' },
            { name: 'AI Food Plating Designer', path: '/ai_food_plating_designer' },
            { name: 'AI Cooking Time Optimizer', path: '/ai_cooking_time_optimizer' },
            { name: 'AI Food History Explorer', path: '/ai_food_history_explorer' },
        ],
    },
];

function HomePage() {
    return (
        <div className="home-page">
            <h1>Welcome to the AI Tools Platform</h1>
            <Link to="/scoolish" className="scoolish-mvp-button">Scoolish</Link>
            <br></br>
            {categories.map((category) => (
                <div key={category.name} className="category">
                    <h2>{category.name}</h2>
                    <div className="tool-cards">
                        {category.tools.map((tool) => (
                            <div key={tool.name} className="tool-card">
                                <h3>{tool.name}</h3>
                                <Link to={tool.path}>Go to {tool.name}</Link>
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}

export default HomePage;