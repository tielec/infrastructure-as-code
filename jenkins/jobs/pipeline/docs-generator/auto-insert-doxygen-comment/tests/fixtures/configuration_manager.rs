use std::collections::HashMap;
use std::error::Error;
use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;

type Result<T> = std::result::Result<T, Box<dyn Error>>;

pub struct ConfigValue {
    value: String,
    description: Option<String>,
    is_secure: bool,
}

impl ConfigValue {
    pub fn new(value: &str, description: Option<&str>, is_secure: bool) -> Self {
        ConfigValue {
            value: value.to_string(),
            description: description.map(|s| s.to_string()),
            is_secure: is_secure,
        }
    }

    pub fn get_value(&self) -> &str {
        &self.value
    }

    pub fn get_masked_value(&self) -> String {
        if self.is_secure && !self.value.is_empty() {
            return "********".to_string();
        }
        self.value.clone()
    }
}

pub struct ConfigurationManager {
    config_data: HashMap<String, ConfigValue>,
    file_path: Option<String>,
    is_modified: bool,
}

impl ConfigurationManager {
    pub fn new() -> Self {
        ConfigurationManager {
            config_data: HashMap::new(),
            file_path: None,
            is_modified: false,
        }
    }

    pub fn load_from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let mut file = File::open(&path)?;
        let mut contents = String::new();
        file.read_to_string(&mut contents)?;

        let mut config = ConfigurationManager::new();
        config.file_path = Some(path.as_ref().to_string_lossy().to_string());

        for line in contents.lines() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }

            if let Some(sep_pos) = line.find('=') {
                let key = line[..sep_pos].trim().to_string();
                let value = line[sep_pos + 1..].trim().to_string();
                
                let is_secure = key.starts_with("password") || 
                               key.starts_with("secret") || 
                               key.starts_with("token");
                
                config.set_value(&key, &value, None, is_secure);
            }
        }

        config.is_modified = false;
        Ok(config)
    }

    pub fn save_to_file<P: AsRef<Path>>(&mut self, path: Option<P>) -> Result<()> {
        let file_path = match path {
            Some(p) => p.as_ref().to_string_lossy().to_string(),
            None => match &self.file_path {
                Some(fp) => fp.clone(),
                None => return Err("No file path specified".into()),
            },
        };

        let mut file = File::create(&file_path)?;
        let mut content = String::new();

        // ヘッダーコメントを追加
        content.push_str("# Configuration File\n");
        content.push_str("# Auto-generated - Do not edit directly\n\n");

        // 設定値を書き込み
        for (key, value) in &self.config_data {
            if let Some(desc) = &value.description {
                content.push_str(&format!("# {}\n", desc));
            }
            content.push_str(&format!("{}={}\n", key, value.get_value()));
        }

        file.write_all(content.as_bytes())?;
        self.file_path = Some(file_path);
        self.is_modified = false;

        Ok(())
    }

    pub fn set_value(&mut self, key: &str, value: &str, description: Option<&str>, is_secure: bool) {
        let config_value = ConfigValue::new(value, description, is_secure);
        self.config_data.insert(key.to_string(), config_value);
        self.is_modified = true;
    }

    pub fn get_value(&self, key: &str) -> Option<&str> {
        self.config_data.get(key).map(|cv| cv.get_value())
    }

    pub fn remove_value(&mut self, key: &str) -> bool {
        let result = self.config_data.remove(key).is_some();
        if result {
            self.is_modified = true;
        }
        result
    }

    pub fn get_all_keys(&self) -> Vec<String> {
        self.config_data.keys().cloned().collect()
    }

    pub fn is_modified(&self) -> bool {
        self.is_modified
    }

    pub fn print_config(&self) {
        println!("Configuration Contents:");
        println!("=======================");
        
        for (key, value) in &self.config_data {
            let display_value = if value.is_secure { value.get_masked_value() } else { value.get_value().to_string() };
            
            if let Some(desc) = &value.description {
                println!("# {}", desc);
            }
            println!("{}={}", key, display_value);
        }
    }
}

fn main() -> Result<()> {
    let mut config = ConfigurationManager::new();
    
    // 設定値の追加
    config.set_value("app.name", "My Application", Some("Application name"), false);
    config.set_value("app.version", "1.0.0", Some("Application version"), false);
    config.set_value("database.url", "jdbc:postgresql://localhost:5432/mydb", Some("Database connection URL"), false);
    config.set_value("database.username", "admin", Some("Database username"), false);
    config.set_value("database.password", "s3cr3t", Some("Database password"), true);
    
    // 設定内容の表示
    config.print_config();
    
    // ファイルへの保存（オプション）
    // config.save_to_file(Some("config.properties"))?;
    
    Ok(())
}
