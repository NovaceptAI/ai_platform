const knowledgeData = {
  id: "root",
  name: "Scoolish WIKI",
  description: "Explorable Knowledge Map",
  children: [
    {
      id: "learning_paths",
      name: "Learning Paths",
      description: "Six curated learning paths → click to explore their stages and tools.",
      children: [
        {
          id: "timeline",
          name: "Timeline Path",
          description: "Discover → Organize → Practice → Create → Collaborate",
          children: [
            { id: "tl_disc", name: "Discover", stage: "Discover", children: [
              { id:"tl_comp", name:"Comparison" },
              { id:"tl_evid", name:"Evidence Extractor" },
              { id:"tl_read", name:"Readability & Style" },
              { id:"tl_chrono", name:"Chronology (date-strict)" },
              { id:"tl_sum", name:"Summarization" },
              { id:"tl_tlx", name:"Timeline Explorer" },
            ]},
            { id: "tl_org", name: "Organize", stage: "Organize", children: [
              { id:"tl_tag", name:"Tag & Taxonomy Manager" },
              { id:"tl_coll", name:"Collections / Boards" },
              { id:"tl_cg", name:"Concept Graph (events/actors map)" },
              { id:"tl_sv", name:"Saved Views" },
            ]},
            { id: "tl_master", name: "Practice & Mastery", stage: "Master", children: [
              { id:"tl_fcards", name:"Customizable Flashcard Creator" },
              { id:"tl_quiz", name:"Interactive Quiz Creator" },
            ]},
            { id: "tl_create", name: "Create", stage: "Create", children: [
              { id:"tl_dsb", name:"Data Story Builder" },
              { id:"tl_htb", name:"Historical Timeline Builder" },
              { id:"tl_aip", name:"AI Presentation Builder" },
            ]},
            { id: "tl_collab", name: "Collaborate", stage: "Collaborate", children: [
              { id:"tl_show", name:"Showcase & Share" },
              { id:"tl_debate", name:"Digital Debate Live" },
              { id:"tl_quizlive", name:"Quiz Competitions Live" },
            ]},
          ],
        },
        {
          id: "codecraft",
          name: "CodeCraft & Systems Thinking",
          description: "Code, systems, and ethical AI practice.",
          children: [
            { id:"cc_disc", name:"Discover", stage:"Discover", children:[
              { id:"cc_comp", name:"Comparison" },
              { id:"cc_sum", name:"Summarization" },
              { id:"cc_doc", name:"Document Analysis" },
              { id:"cc_seg", name:"Segmentation - docs/papers" },
            ]},
            { id:"cc_org", name:"Organize", stage:"Organize", children:[
              { id:"cc_tag", name:"Tag & Taxonomy Manager" },
              { id:"cc_coll", name:"Collections / Boards" },
              { id:"cc_cluster", name:"Cluster Builder" },
              { id:"cc_cg", name:"Concept Graph" },
              { id:"cc_sv", name:"Saved Views" },
            ]},
            { id:"cc_master", name:"Practice & Mastery", stage:"Master", children:[
              { id:"cc_ethics", name:"Ethical AI Tutor" },
              { id:"cc_fcards", name:"Customizable Flashcard Creator" },
              { id:"cc_hw", name:"AI Homework Creator & Helper" },
              { id:"cc_quiz", name:"Interactive Quiz Creator" },
              { id:"cc_code", name:"Code Playground - AI Coding" },
            ]},
            { id:"cc_create", name:"Create", stage:"Create", children:[
              { id:"cc_dsb", name:"Data Story Builder" },
              { id:"cc_aip", name:"AI Presentation Builder" },
            ]},
            { id:"cc_collab", name:"Collaborate", stage:"Collaborate", children:[
              { id:"cc_quizlive", name:"Quiz Competitions Live" },
              { id:"cc_mindmap", name:"Collaborative Mind Mapping" },
              { id:"cc_pair", name:"Co-authoring - Pair Programming" },
              { id:"cc_show", name:"Showcase & Share" },
            ]},
          ],
        },
        {
          id: "deep_reading",
          name: "Deep Reading & Investigation",
          description: "Close reading, evidence, and research.",
          children: [
            { id:"dr_disc", name:"Discover", stage:"Discover", children:[
              { id:"dr_chrono", name:"Chronology" },
              { id:"dr_sum", name:"Summarization" },
              { id:"dr_seg", name:"Segmentation" },
              { id:"dr_read", name:"Readability & Style" },
              { id:"dr_evid", name:"Evidence Extractor" },
              { id:"dr_doc", name:"Document Analysis" },
              { id:"dr_comp", name:"Comparison" },
            ]},
            { id:"dr_org", name:"Organize", stage:"Organize", children:[
              { id:"dr_coll", name:"Collections / Boards" },
              { id:"dr_tag", name:"Tag & Taxonomy Manager" },
              { id:"dr_cluster", name:"Cluster Builder" },
              { id:"dr_cg", name:"Concept Graph" },
              { id:"dr_sv", name:"Saved Views" },
            ]},
            { id:"dr_master", name:"Practice & Mastery", stage:"Master", children:[
              { id:"dr_fcards", name:"Customizable Flashcard Creator" },
              { id:"dr_hw", name:"AI Homework Creator & Helper" },
              { id:"dr_vsg", name:"Visual Study Guide / Study Pack" },
              { id:"dr_quiz", name:"Interactive Quiz Creator" },
            ]},
            { id:"dr_create", name:"Create", stage:"Create", children:[
              { id:"dr_cwp", name:"Creative Writing Prompts" },
              { id:"dr_dsb", name:"Data Story Builder" },
              { id:"dr_aip", name:"AI Presentation Builder" },
            ]},
            { id:"dr_collab", name:"Collaborate", stage:"Collaborate", children:[
              { id:"dr_peer", name:"Co-authoring & Peer Review" },
              { id:"dr_show", name:"Showcase & Share" },
            ]},
          ],
        },
        {
          id: "stem",
          name: "STEM Fundamentals",
          description: "Math, science, challenges, and presentations.",
          children: [
            { id:"st_disc", name:"Discover", stage:"Discover", children:[
              { id:"st_comp", name:"Comparison" },
              { id:"st_sum", name:"Summarization" },
              { id:"st_doc", name:"Document Analysis" },
              { id:"st_seg", name:"Segmentation" },
            ]},
            { id:"st_org", name:"Organize", stage:"Organize", children:[
              { id:"st_tag", name:"Tag & Taxonomy Manager" },
              { id:"st_coll", name:"Collections / Boards" },
              { id:"st_cluster", name:"Cluster Builder" },
              { id:"st_cg", name:"Concept Graph" },
              { id:"st_std", name:"Standards Alignment" },
              { id:"st_sv", name:"Saved Views" },
            ]},
            { id:"st_master", name:"Practice & Mastery", stage:"Master", children:[
              { id:"st_math", name:"Math Problem Visualizer" },
              { id:"st_lab", name:"Virtual Science Lab" },
              { id:"st_chal", name:"STEM Challenge Generator" },
              { id:"st_hw", name:"AI Homework Creator & Helper" },
              { id:"st_quiz", name:"Interactive Quiz Creator" },
            ]},
            { id:"st_create", name:"Create", stage:"Create", children:[
              { id:"st_3d", name:"3D Model Builder" },
              { id:"st_aip", name:"AI Presentation Builder" },
            ]},
            { id:"st_collab", name:"Collaborate", stage:"Collaborate", children:[
              { id:"st_show", name:"Showcase & Share" },
            ]},
          ],
        },
        {
          id: "language",
          name: "Language Learning",
          description: "Leveling, vocab, games, comics, and peer review.",
          children: [
            { id:"la_disc", name:"Discover", stage:"Discover", children:[
              { id:"la_sum", name:"Summarization" },
              { id:"la_sent", name:"Sentiment Analysis" },
              { id:"la_doc", name:"Document Analysis" },
              { id:"la_seg", name:"Segmentation" },
              { id:"la_read", name:"Readability / Leveling" },
            ]},
            { id:"la_org", name:"Organize", stage:"Organize", children:[
              { id:"la_coll", name:"Collections / Boards" },
              { id:"la_sv", name:"Saved Views" },
              { id:"la_cefr", name:"Tag & Taxonomy CEFR" },
            ]},
            { id:"la_master", name:"Practice & Mastery", stage:"Master", children:[
              { id:"la_draw", name:"Learn by Drawing (vocab/concepts)" },
              { id:"la_fcards", name:"Customizable Flashcard Creator" },
              { id:"la_hw", name:"AI Homework Creator & Helper" },
              { id:"la_quiz", name:"Interactive Quiz Creator" },
              { id:"la_games", name:"Language Learning Games / Coach" },
            ]},
            { id:"la_create", name:"Create", stage:"Create", children:[
              { id:"la_strip", name:"Interactive Comic Strip Builder" },
              { id:"la_comics", name:"Story to Comics Converter" },
              { id:"la_cwp", name:"Creative Writing Prompts" },
              { id:"la_aip", name:"AI Presentation Builder" },
            ]},
            { id:"la_collab", name:"Collaborate", stage:"Collaborate", children:[
              { id:"la_quizlive", name:"Quiz Competitions Live" },
              { id:"la_peer", name:"Co-authoring & Peer Review" },
              { id:"la_show", name:"Showcase & Share" },
            ]},
          ],
        },
        {
          id: "creative",
          name: "Creative Arts & Media",
          description: "Prompts, visualization, comics, AI art, and 3D.",
          children: [
            { id:"ca_disc", name:"Discover", stage:"Discover", children:[
              { id:"ca_sent", name:"Sentiment Analysis" },
              { id:"ca_sum", name:"Summarization" },
              { id:"ca_seg", name:"Segmentation" },
              { id:"ca_doc", name:"Document Analysis" },
            ]},
            { id:"ca_org", name:"Organize", stage:"Organize", children:[
              { id:"ca_tag", name:"Tag & Taxonomy Manager" },
              { id:"ca_coll", name:"Collections / Boards" },
              { id:"ca_cluster", name:"Cluster Builder" },
              { id:"ca_sv", name:"Saved Views" },
            ]},
            { id:"ca_master", name:"Practice & Mastery", stage:"Master", children:[
              { id:"ca_ethics", name:"Ethical AI Tutor" },
              { id:"ca_fcards", name:"Customizable Flashcard Creator - A-I-M-A-D-M-S-C" },
              { id:"ca_cps", name:"Creative Prompt Studio" },
              { id:"ca_storyviz", name:"Story Visualization" },
            ]},
            { id:"ca_create", name:"Create", stage:"Create", children:[
              { id:"ca_strip", name:"Interactive Comic Strip Builder" },
              { id:"ca_aip", name:"AI Presentation Builder" },
              { id:"ca_dsb", name:"Data Story Builder" },
              { id:"ca_art", name:"AI Art Creator for Kids" },
              { id:"ca_3d", name:"3D Model Builder" },
              { id:"ca_storyviz2", name:"Story Visualizer" },
              { id:"ca_story2comics", name:"Story → Comics Converter" },
            ]},
            { id:"ca_collab", name:"Collaborate", stage:"Collaborate", children:[
              { id:"ca_show", name:"Showcase & Share" },
              { id:"ca_mindmap", name:"Collaborative Mind Map" },
            ]},
          ],
        },
      ],
    },
    {
      id: "research",
      name: "Research",
      description: "Workspace: API Scraper, AI Browser, AI Chat, Live Knowledge, Vault.",
      children: [
        {
          id: "rs_api",
          name: "API Scraper",
          description: "Collect data from web sources in real time; export JSON/CSV/PDF; on-screen JSON viewer; geo-smart proxies.",
          children: [
            {
              id: "rs_api_features",
              name: "Crawler Features",
              children: [
                { id: "rs_api_feat_realtime", name: "Real-time collection based on user query" },
                { id: "rs_api_feat_json", name: "Results in JSON" },
                { id: "rs_api_feat_csv", name: "Export: CSV" },
                { id: "rs_api_feat_pdf", name: "Export: PDF" },
                { id: "rs_api_feat_view", name: "On-screen JSON viewer" },
                { id: "rs_api_feat_proxy", name: "Nearest proxies by Google geo" },
                { id: "rs_api_feat_quality", name: "Highest quality / best uptime" },
                { id: "rs_api_feat_now", name: "Each API runs immediately" },
                { id: "rs_api_feat_curate", name: "Curate your dataset" },
                { id: "rs_api_feat_catalog", name: "Use available datasets" }
              ]
            },
            {
              id: "rs_api_search_types",
              name: "Search Types",
              children: [
                { id: "rs_api_search_engine", name: "Search Engine" },
                { id: "rs_api_images", name: "Images" },
                { id: "rs_api_shopping", name: "Shopping" },
                { id: "rs_api_maps", name: "Maps" },
                { id: "rs_api_videos", name: "Videos" },
                { id: "rs_api_hotels", name: "Hotels" },
                { id: "rs_api_entertainment", name: "Entertainment Facilities" }
              ]
            },
            {
              id: "rs_api_sources",
              name: "Source Categories",
              children: [
                {
                  id: "rs_api_social",
                  name: "Social Media",
                  children: [
                    { id: "rs_api_fb", name: "Facebook" },
                    { id: "rs_api_ig", name: "Instagram" },
                    { id: "rs_api_tw", name: "Twitter" },
                    { id: "rs_api_tt", name: "TikTok" },
                    { id: "rs_api_li", name: "LinkedIn" },
                    { id: "rs_api_pin", name: "Pinterest" },
                    { id: "rs_api_snap", name: "Snapchat" },
                    { id: "rs_api_tumblr", name: "Tumblr" },
                    { id: "rs_api_quora", name: "Quora" },
                    { id: "rs_api_flickr", name: "Flickr" },
                    { id: "rs_api_yt", name: "YouTube" },
                    { id: "rs_api_dm", name: "Dailymotion" },
                    { id: "rs_api_vimeo", name: "Vimeo" }
                  ]
                },
                {
                  id: "rs_api_search",
                  name: "Search Engines",
                  children: [
                    { id: "rs_api_google", name: "Google Search" },
                    { id: "rs_api_bing", name: "Bing Search" },
                    { id: "rs_api_baidu", name: "Baidu Search" },
                    { id: "rs_api_tor", name: "TorSearch" },
                    { id: "rs_api_yandex", name: "Yandex" }
                  ]
                },
                {
                  id: "rs_api_music",
                  name: "Music",
                  children: [
                    { id: "rs_api_spotify", name: "Spotify" },
                    { id: "rs_api_itunes", name: "Apple iTunes" }
                  ]
                },
                {
                  id: "rs_api_edu",
                  name: "Educational / Literature / Library",
                  children: [
                    { id: "rs_api_scholar", name: "Google Scholar" },
                    { id: "rs_api_wws", name: "WorldWideScience.org" },
                    { id: "rs_api_books", name: "Google Books" },
                    { id: "rs_api_worldcat", name: "WorldCat" },
                    { id: "rs_api_ocl", name: "OCL API" },
                    { id: "rs_api_openlib", name: "Open Library" },
                    { id: "rs_api_wikipedia", name: "Wikipedia" },
                    { id: "rs_api_medium", name: "Medium" },
                    { id: "rs_api_udemy", name: "Udemy" }
                  ]
                },
                {
                  id: "rs_api_appstores",
                  name: "App Stores",
                  children: [
                    { id: "rs_api_play", name: "Google Play" },
                    { id: "rs_api_appstore", name: "Apple Store" }
                  ]
                },
                {
                  id: "rs_api_ecom",
                  name: "E-commerce",
                  children: [
                    { id: "rs_api_amazon", name: "Amazon" },
                    { id: "rs_api_ebay", name: "Ebay" }
                  ]
                },
                {
                  id: "rs_api_others",
                  name: "Others",
                  children: [
                    { id: "rs_api_revimg", name: "Google Reverse Image" },
                    { id: "rs_api_products", name: "Google Products" },
                    { id: "rs_api_so", name: "Stack Overflow" },
                    { id: "rs_api_yanswers", name: "Yahoo Answers (offline since May 4, 2021)" }
                  ]
                }
              ]
            }
          ]
        },
        { id: "rs_browser", name: "AI Browser" },
        { id: "rs_chat", name: "AI Chat" },
        { id: "rs_live", name: "Live Knowledge Tracking" },
        { id: "rs_vault", name: "Knowledge Vault" }
      ]
    }
,
    {
      id: "onboarding",
      name: "User Onboarding",
      description: "Learner / Educator / Professional / Organization flows.",
      children: [
        { id:"ob_learner", name:"Learner Flow" },
        { id:"ob_educator", name:"Educator Flow" },
        { id:"ob_prof", name:"Professional Flow" },
        { id:"ob_org", name:"Organizational Flow" },
      ],
    },
    {
      id: "rules",
      name: "Rules & Regulations",
      description: "File types, limits, governance, compliance, QA, and auditing.",
      children: [
        { id:"ru_types", name:"Supported File Types", children: [
          { id:"ru_types_list", name:"PDF, DOCX, PPTX, CSV, TXT, JSON, Audio, Video" }
        ]},
        { id:"ru_limits", name:"File Size Limits", children: [
          { id:"ru_limits_max", name:"Max file size: ~500MB (configurable)" }
        ]},

        {
          id: "ru_governance",
          name: "Governance & Compliance",
          description: "Access control, privacy, standards, QA, monitoring.",
          children: [
            { id: "ru_perm", name: "Permissions & Access Control", children: [
              { id:"ru_perm_roles", name:"Roles: Learner, Educator, Professional, Org Admin" },
              { id:"ru_perm_proj",  name:"Project permissions: Owner, Collaborator, Viewer" },
              { id:"ru_perm_vault", name:"Vault access: Private, Shared, Org-wide" },
              { id:"ru_perm_audit", name:"Audit logging: who accessed what, when" },
            ]},

            { id: "ru_privacy", name: "Data Privacy", children: [
              { id:"ru_priv_vault",   name:"Storage: Azure Blob (Knowledge Vault)" },
              { id:"ru_priv_crypto",  name:"Encryption: at-rest (AES-256), in-transit (TLS 1.2+)" },
              { id:"ru_priv_ret",     name:"Retention: default 1 year (configurable)" },
              { id:"ru_priv_erase",   name:"Right-to-erase: deletion upon request" },
            ]},

            { id: "ru_data", name: "File & Data Handling", children: [
              { id:"ru_data_val",   name:"Upload validation & virus scanning" },
              { id:"ru_data_export",name:"Exports: JSON, CSV, PDF" },
              { id:"ru_data_types", name:"Data formats: text, tables, images, transcripts, JSON" },
            ]},

            { id: "ru_compliance", name: "Compliance Standards", children: [
              { id:"ru_comp_ferpa", name:"FERPA/GDPR alignment (education & EU users)" },
              { id:"ru_comp_policy",name:"Internal governance policy & approvals" },
              { id:"ru_comp_auth",  name:"JWT-secured APIs & least-privilege access" },
              { id:"ru_comp_patch", name:"Regular patching & security monitoring" },
            ]},

            { id: "ru_qa", name: "Quality Assurance", children: [
              { id:"ru_qa_review", name:"Review queue (educator/admin approval)" },
              { id:"ru_qa_hitl",   name:"Human-in-the-loop for sensitive outputs" },
              { id:"ru_qa_dedupe", name:"Deduplication & merge in Knowledge Vault" },
              { id:"ru_qa_version",name:"Version control for datasets/projects" },
            ]},

            { id: "ru_monitor", name: "Monitoring & Reporting", children: [
              { id:"ru_mon_audit", name:"Audit logs: uploads/edits/exports" },
              { id:"ru_mon_dash",  name:"Admin dashboards for compliance metrics" },
              { id:"ru_mon_alert", name:"Alerts for suspicious activity & failed ingestion" },
            ]},
          ],
        },
      ],
    },
    {
      id: "roles",
      name: "Roles & Groups",
      description: "Learner, Educator, Professional, Organization; Teams, Study Groups, Cohorts.",
      children: [
        { id:"ro_roles", name:"Roles: Learner, Educator, Professional, Organization" },
        { id:"ro_groups", name:"Groups: Project Teams, Study Groups, Classroom Cohorts" },
      ],
    },
    {
      id: "models",
      name: "AI Models",
      description: "Hosted GPT, in-house fine-tunes, and open-source models.",
      children: [
        { id:"mo_gpt", name:"GPT (Hosted): GPT-4, GPT-4o" },
        { id:"mo_inhouse", name:"In-House (Fine-Tuned): Domain chats, Summarizers, Recommenders" },
        { id:"mo_oss", name:"Open-Source: LLaMA, Falcon, MPT" },
      ],
    },
  ],
};

export default knowledgeData;