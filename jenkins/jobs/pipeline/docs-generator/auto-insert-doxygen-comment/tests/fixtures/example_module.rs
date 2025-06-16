// src/main.rs
mod models;
mod repositories;
mod services;
mod utils;

use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, BufReader, BufRead, Write};
use std::path::Path;

use models::{Task, TaskStatus, User};
use repositories::{TaskRepository, UserRepository};
use services::TaskService;
use utils::{Logger, Result, AppError};

fn load_users_from_file(filepath: &str) -> Result<Vec<User>> {
    let path = Path::new(filepath);
    let file = File::open(path).map_err(|e| AppError::IoError(format!("ファイルオープンエラー: {}", e)))?;
    let reader = BufReader::new(file);
    
    let mut users = Vec::new();
    
    for line in reader.lines() {
        let line = line.map_err(|e| AppError::ParseError(format!("行の読み込みエラー: {}", e)))?;
        let parts: Vec<&str> = line.split(',').collect();
        
        if parts.len() >= 2 {
            let id = parts[0].parse::<u64>()
                .map_err(|_| AppError::ParseError(format!("ID解析エラー: {}", parts[0])))?;
            let name = parts[1].to_string();
            let email = if parts.len() > 2 { Some(parts[2].to_string()) } else { None };
            
            users.push(User::new(id, name, email));
        } else {
            return Err(AppError::ParseError(format!("不正なユーザーデータ形式: {}", line)));
        }
    }
    
    Ok(users)
}

fn process_tasks(tasks: Arc<Mutex<Vec<Task>>>, service: Arc<TaskService>, logger: Arc<Logger>) {
    let mut handles = vec![];
    
    // 複数スレッドでタスクを処理
    for _ in 0..4 {
        let tasks_clone = Arc::clone(&tasks);
        let service_clone = Arc::clone(&service);
        let logger_clone = Arc::clone(&logger);
        
        let handle = thread::spawn(move || {
            loop {
                let task_option = {
                    let mut tasks = tasks_clone.lock().unwrap();
                    // 未処理のタスクを探す
                    let pos = tasks.iter().position(|t| t.status == TaskStatus::Pending);
                    
                    if let Some(pos) = pos {
                        let mut task = tasks[pos].clone();
                        task.status = TaskStatus::InProgress;
                        tasks[pos] = task.clone();
                        Some(task)
                    } else {
                        None
                    }
                };
                
                if let Some(mut task) = task_option {
                    // タスク処理をシミュレート
                    logger_clone.log(&format!("タスク処理開始: ID={}, 名前={}", task.id, task.name));
                    thread::sleep(Duration::from_millis(500));
                    
                    // タスクの処理
                    match service_clone.process_task(&task) {
                        Ok(_) => {
                            task.status = TaskStatus::Completed;
                            logger_clone.log(&format!("タスク完了: ID={}", task.id));
                        },
                        Err(e) => {
                            task.status = TaskStatus::Failed;
                            logger_clone.log(&format!("タスク失敗: ID={}, エラー={}", task.id, e));
                        }
                    }
                    
                    // タスクステータスを更新
                    let mut tasks = tasks_clone.lock().unwrap();
                    for t in tasks.iter_mut() {
                        if t.id == task.id {
                            *t = task.clone();
                            break;
                        }
                    }
                } else {
                    // 処理するタスクがなければ終了
                    break;
                }
            }
        });
        
        handles.push(handle);
    }
    
    // すべてのスレッドの完了を待つ
    for handle in handles {
        handle.join().unwrap();
    }
}

fn main() -> Result<()> {
    let logger = Arc::new(Logger::new());
    logger.log("アプリケーション起動");
    
    // リポジトリのセットアップ
    let user_repo = Arc::new(UserRepository::new());
    let task_repo = Arc::new(TaskRepository::new());
    
    // サービスの作成
    let task_service = Arc::new(TaskService::new(Arc::clone(&user_repo), Arc::clone(&task_repo)));
    
    // ユーザーデータの読み込み
    match load_users_from_file("./users.csv") {
        Ok(users) => {
            logger.log(&format!("{}人のユーザーを読み込み完了", users.len()));
            for user in users {
                user_repo.add(user);
            }
        },
        Err(e) => {
            logger.log(&format!("ユーザーデータ読み込みエラー: {}", e));
            return Err(e);
        }
    };
    
    // タスクの作成
    let tasks = vec![
        Task::new(1, "データ集計".to_string(), 1),
        Task::new(2, "レポート作成".to_string(), 2),
        Task::new(3, "メール送信".to_string(), 1),
        Task::new(4, "バックアップ".to_string(), 3),
        Task::new(5, "コード最適化".to_string(), 2),
    ];
    
    // タスクをリポジトリとプロセス用の共有データに追加
    let shared_tasks = Arc::new(Mutex::new(Vec::new()));
    for task in tasks {
        task_repo.add(task.clone());
        shared_tasks.lock().unwrap().push(task);
    }
    
    logger.log(&format!("{}個のタスクを作成", task_repo.count()));
    
    // 並行タスク処理
    process_tasks(shared_tasks.clone(), task_service.clone(), logger.clone());
    
    // 結果の集計
    let tasks = shared_tasks.lock().unwrap();
    
    let mut status_counts = HashMap::new();
    for task in tasks.iter() {
        *status_counts.entry(task.status).or_insert(0) += 1;
    }
    
    logger.log("\n=== タスク処理結果 ===");
    for (status, count) in status_counts.iter() {
        logger.log(&format!("{:?}: {} 件", status, count));
    }
    
    // 詳細ログ出力
    logger.log("\n=== 詳細ログ ===");
    for task in tasks.iter() {
        let assigned_user = user_repo.get_by_id(task.assigned_to)
            .map(|u| u.name.clone())
            .unwrap_or_else(|| "不明".to_string());
        
        logger.log(&format!(
            "タスクID: {}, 名前: {}, 担当者: {}, ステータス: {:?}",
            task.id, task.name, assigned_user, task.status
        ));
    }
    
    logger.log("アプリケーション終了");
    Ok(())
}

// src/models.rs
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TaskStatus {
    Pending,
    InProgress,
    Completed,
    Failed,
}

#[derive(Debug, Clone)]
pub struct Task {
    pub id: u64,
    pub name: String,
    pub assigned_to: u64,
    pub status: TaskStatus,
}

impl Task {
    pub fn new(id: u64, name: String, assigned_to: u64) -> Self {
        Self {
            id,
            name,
            assigned_to,
            status: TaskStatus::Pending,
        }
    }
}

#[derive(Debug, Clone)]
pub struct User {
    pub id: u64,
    pub name: String,
    pub email: Option<String>,
}

impl User {
    pub fn new(id: u64, name: String, email: Option<String>) -> Self {
        Self { id, name, email }
    }
}

// src/repositories.rs
use std::sync::Mutex;
use crate::models::{Task, User};

pub struct UserRepository {
    users: Mutex<Vec<User>>,
}

impl UserRepository {
    pub fn new() -> Self {
        Self {
            users: Mutex::new(Vec::new()),
        }
    }
    
    pub fn add(&self, user: User) {
        let mut users = self.users.lock().unwrap();
        users.push(user);
    }
    
    pub fn get_by_id(&self, id: u64) -> Option<User> {
        let users = self.users.lock().unwrap();
        users.iter().find(|u| u.id == id).cloned()
    }
    
    pub fn count(&self) -> usize {
        let users = self.users.lock().unwrap();
        users.len()
    }
}

pub struct TaskRepository {
    tasks: Mutex<Vec<Task>>,
}

impl TaskRepository {
    pub fn new() -> Self {
        Self {
            tasks: Mutex::new(Vec::new()),
        }
    }
    
    pub fn add(&self, task: Task) {
        let mut tasks = self.tasks.lock().unwrap();
        tasks.push(task);
    }
    
    pub fn get_by_id(&self, id: u64) -> Option<Task> {
        let tasks = self.tasks.lock().unwrap();
        tasks.iter().find(|t| t.id == id).cloned()
    }
    
    pub fn count(&self) -> usize {
        let tasks = self.tasks.lock().unwrap();
        tasks.len()
    }
}

// src/services.rs
use std::sync::Arc;
use rand::Rng;
use crate::models::Task;
use crate::repositories::{UserRepository, TaskRepository};
use crate::utils::{Result, AppError};

pub struct TaskService {
    user_repository: Arc<UserRepository>,
    task_repository: Arc<TaskRepository>,
}

impl TaskService {
    pub fn new(
        user_repository: Arc<UserRepository>,
        task_repository: Arc<TaskRepository>
    ) -> Self {
        Self {
            user_repository,
            task_repository,
        }
    }
    
    pub fn process_task(&self, task: &Task) -> Result<()> {
        // 担当ユーザーが存在するか確認
        if self.user_repository.get_by_id(task.assigned_to).is_none() {
            return Err(AppError::BusinessError(
                format!("タスク {} の担当者 (ID={}) が見つかりません", task.id, task.assigned_to)
            ));
        }
        
        // タスク処理のシミュレーション - 10%の確率で失敗
        let mut rng = rand::thread_rng();
        if rng.gen_range(0..10) == 0 {
            return Err(AppError::BusinessError("タスク処理中にランダムエラーが発生しました".to_string()));
        }
        
        Ok(())
    }
}

// src/utils.rs
use std::fmt;
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

pub type Result<T> = std::result::Result<T, AppError>;

#[derive(Debug)]
pub enum AppError {
    IoError(String),
    ParseError(String),
    BusinessError(String),
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            AppError::IoError(msg) => write!(f, "I/Oエラー: {}", msg),
            AppError::ParseError(msg) => write!(f, "解析エラー: {}", msg),
            AppError::BusinessError(msg) => write!(f, "ビジネスロジックエラー: {}", msg),
        }
    }
}

pub struct Logger {
    logs: Mutex<Vec<String>>,
}

impl Logger {
    pub fn new() -> Self {
        Self {
            logs: Mutex::new(Vec::new()),
        }
    }
    
    pub fn log(&self, message: &str) {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        let log_entry = format!("[{}] {}", timestamp, message);
        println!("{}", log_entry);
        
        let mut logs = self.logs.lock().unwrap();
        logs.push(log_entry);
    }
    
    pub fn get_logs(&self) -> Vec<String> {
        let logs = self.logs.lock().unwrap();
        logs.clone()
    }
}

// ユーザーデータ例 (users.csv)
// 1,田中太郎,tanaka@example.com
// 2,鈴木花子,suzuki@example.com
// 3,佐藤次郎,sato@example.com
