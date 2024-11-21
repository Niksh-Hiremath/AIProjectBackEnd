module.exports = {
  apps: [
    {
      name: "aiback",
      script: "main.py",
      watch: false,
      autorestart: true,
      restart_delay: 5000,
      time: true
    }
  ]
}