module.exports = {
  apps: [
    {
      name: 'bruno-gmail',
      script: 'scripts/gmail_monitor.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      error_file: 'logs/gmail_error.log',
      out_file: 'logs/gmail_out.log',
      merge_logs: true
    },
    {
      name: 'bruno-inventario',
      script: 'scripts/inventario_monitor.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      error_file: 'logs/inventario_error.log',
      out_file: 'logs/inventario_out.log',
      merge_logs: true
    }
  ]
};
