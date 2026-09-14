// SPDX-License-Identifier: GPL-2.0
/* T95H late WLAN supply plus bounded CPU DVFS and read-only GPU supply. */
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/regmap.h>
#include <linux/regulator/driver.h>
#include <linux/regulator/machine.h>
#include <linux/regulator/of_regulator.h>
#include <linux/delay.h>

static int supply_enable(struct regulator_dev *rdev)
{
 struct regmap *map = rdev_get_drvdata(rdev);
 unsigned int ctl, voltage; int ret;
 ret=regmap_read(map,0x10,&ctl); if(ret)return ret;
 ret=regmap_read(map,0x18,&voltage); if(ret)return ret;
 if ((ctl & 0x40) && voltage == 0x1a) return 0;
 if ((ctl & 0x40) || (voltage != 0 && voltage != 0x1a)) return -EINVAL;
 ret=regmap_write(map,0x18,0x1a); if(ret)return ret;
 ret=regmap_read(map,0x18,&voltage); if(ret)return ret;
 if(voltage!=0x1a)return -EIO;
 usleep_range(10000,12000);
 ret=regmap_update_bits(map,0x10,0x40,0x40); if(ret)return ret;
 ret=regmap_read(map,0x10,&ctl); if(ret)return ret;
 if(!(ctl&0x40))return -EIO;
 dev_info(&rdev->dev,"ALDO2 3300mV enabled before SDIO probe\n");
 return 0;
}
static int supply_enabled(struct regulator_dev *rdev)
{
 unsigned int ctl, voltage; struct regmap *map=rdev_get_drvdata(rdev); int ret;
 ret=regmap_read(map,0x10,&ctl); if(ret)return ret;
 ret=regmap_read(map,0x18,&voltage); if(ret)return ret;
 return (ctl & 0x40) && voltage == 0x1a;
}
static const struct regulator_ops ops = {
 .enable=supply_enable, .is_enabled=supply_enabled,
 .list_voltage=regulator_list_voltage_linear,
};
static const struct regulator_desc desc = {
 .name="t95h-aldo2-wlan", .owner=THIS_MODULE, .type=REGULATOR_VOLTAGE,
 .ops=&ops, .n_voltages=1, .min_uV=3300000, .fixed_uV=3300000,
 .enable_time=100000,
};
static bool writable(struct device *dev, unsigned int reg)
{
 return reg==0x10 || reg==0x12 || reg==0x18;
}
static const struct regmap_config mapcfg = {
 .reg_bits=8, .val_bits=8, .max_register=0xff,
 .cache_type=REGCACHE_NONE, .writeable_reg=writable,
};
/* AXP806-compatible DCDCA encoding, corroborated by Android regulator data.
 * One PMIC owner: keep the original late ALDO2 sequence, add CPU DVFS and
 * read-only GPU supply. CPU regulator core orders voltage before clock-up
 * and after clock-down. Never disable CPU/GPU or touch other rail settings.
 */
static int t95h_cpu_enabled(struct regulator_dev *rdev)
{
 unsigned int v; int ret=regmap_read(rdev_get_drvdata(rdev),0x10,&v);
 return ret ? ret : !!(v & 1);
}
static int t95h_cpu_get_sel(struct regulator_dev *rdev)
{
 unsigned int v; int ret=regmap_read(rdev_get_drvdata(rdev),0x12,&v);
 if(ret)return ret;
 v &= 0x7f;
 return (v>=30 && v<=51) ? v : -ERANGE;
}
static int t95h_cpu_set_sel(struct regulator_dev *rdev, unsigned int sel)
{
 struct regmap *map=rdev_get_drvdata(rdev); unsigned int ctl,readback;
 int old,ret,next;
 if(sel<30 || sel>51)return -EINVAL;
 ret=regmap_read(map,0x10,&ctl);if(ret)return ret;
 if(!(ctl&1))return -EPERM;
 old=t95h_cpu_get_sel(rdev);if(old<0)return old;
 while(old!=sel) {
  next=old+(old<(int)sel ? 1 : -1);
  ret=regmap_update_bits(map,0x12,0x7f,next);if(ret)return ret;
  usleep_range(100,150);
  ret=regmap_read(map,0x12,&readback);if(ret)return ret;
  if((readback&0x7f)!=next)return -EIO;
  old=next;
 }
 usleep_range(100,150);
 return 0;
}
static const struct linear_range cpu_ranges[] = {
 REGULATOR_LINEAR_RANGE(600000,0,50,10000),
 REGULATOR_LINEAR_RANGE(1120000,51,51,0),
};
static const struct regulator_ops cpu_ops = {
 .is_enabled=t95h_cpu_enabled, .get_voltage_sel=t95h_cpu_get_sel,
 .set_voltage_sel=t95h_cpu_set_sel,
 .list_voltage=regulator_list_voltage_linear_range,
 .map_voltage=regulator_map_voltage_linear_range,
};
static const struct regulator_desc cpu_desc = {
 .name="t95h-cpu-dcdca", .owner=THIS_MODULE,
 .type=REGULATOR_VOLTAGE, .ops=&cpu_ops, .n_voltages=52,
 .linear_ranges=cpu_ranges, .n_linear_ranges=ARRAY_SIZE(cpu_ranges),
};
static int gpu_enabled(struct regulator_dev *rdev)
{
 unsigned int v;int ret=regmap_read(rdev_get_drvdata(rdev),0x10,&v);
 return ret ? ret : !!(v&4);
}
static int gpu_voltage(struct regulator_dev *rdev)
{
 unsigned int v;int ret=regmap_read(rdev_get_drvdata(rdev),0x14,&v);
 if(ret)return ret;
 v &= 0x7f;
 return v==36 ? 960000 : (v==50 ? 1100000 : -ERANGE);
}
/* A read-only supply may accept a range already satisfied by hardware.
 * Never advertise that we can change this rail to a requested exact voltage. */
static int gpu_accept_voltage(struct regulator_dev *rdev,int min,int max,
                              unsigned int *selector)
{
 int uv=gpu_voltage(rdev);
 if(uv<0)return uv;
 if(uv<min || uv>max)return -EINVAL;
 *selector=uv==960000 ? 0 : 1;
 return 0;
}
static const unsigned int gpu_voltages[] = {960000,1100000};
static const struct regulator_ops gpu_ops = {
 .is_enabled=gpu_enabled, .get_voltage=gpu_voltage,
 .set_voltage=gpu_accept_voltage, .list_voltage=regulator_list_voltage_table,
};
static const struct regulator_desc gpu_desc = {
 .name="t95h-gpu-inherited", .owner=THIS_MODULE,
 .type=REGULATOR_VOLTAGE, .ops=&gpu_ops, .n_voltages=2,
 .volt_table=gpu_voltages,
};
static void register_compute_supply(struct i2c_client *client, struct regmap *map,
                                   bool gpu)
{
 const struct regulator_desc *d=gpu ? &gpu_desc : &cpu_desc;
 struct device_node *node=of_get_child_by_name(client->dev.of_node,
                                  gpu ? "gpu-regulator" : "cpu-regulator");
 struct regulator_config cfg={};struct regulator_dev *rdev;
 unsigned int ctl=0,voltage=0;int ret;
 if(!node)return;
 ret=regmap_read(map,0x10,&ctl);
 if(!ret)ret=regmap_read(map,gpu ? 0x14 : 0x12,&voltage);
 voltage &= 0x7f;
 if(ret || !(ctl&(gpu ? 4 : 1)) ||
    (gpu ? (voltage!=36 && voltage!=50) : (voltage<30 || voltage>51))) {
  dev_warn(&client->dev,"%s unexpected initial supply state; registration refused, WLAN preserved\n",d->name);
  goto out;
 }
 cfg.dev=&client->dev;cfg.of_node=node;cfg.driver_data=map;
 cfg.init_data=of_get_regulator_init_data(&client->dev,node,d);
 if(!cfg.init_data || !cfg.init_data->constraints.always_on ||
    cfg.init_data->constraints.min_uV!=(gpu ? 960000 : 900000) ||
    cfg.init_data->constraints.max_uV!=(gpu ? 1100000 : 1120000))goto out;
 rdev=devm_regulator_register(&client->dev,d,&cfg);
 if(IS_ERR(rdev))dev_warn(&client->dev,"%s registration failed: %ld\n",d->name,PTR_ERR(rdev));
 else dev_info(&client->dev,"%s registered; %s\n",d->name,
               gpu ? "GPU supply read-only: accept measured 960mV or 1100mV" : "CPU DVFS range 900-1120mV with step/readback verification");
 out:of_node_put(node);
}

static int supply_probe(struct i2c_client *client)
{
 struct regmap *map; struct regulator_config cfg={};
 struct regulator_dev *rdev; unsigned int id, ctl, voltage; int ret;
 map=devm_regmap_init_i2c(client,&mapcfg); if(IS_ERR(map))return PTR_ERR(map);
 ret=regmap_read(map,3,&id); if(ret)return ret;
 if(id!=0x60)return dev_err_probe(&client->dev,-ENODEV,"Unexpected PMIC ID %02x\n",id);
 ret=regmap_read(map,0x10,&ctl); if(ret)return ret;
 ret=regmap_read(map,0x18,&voltage); if(ret)return ret;
 if(((ctl&0x40) && voltage!=0x1a) || (!(ctl&0x40) && voltage!=0 && voltage!=0x1a))
  return dev_err_probe(&client->dev,-EINVAL,"Unexpected ALDO2 state\n");
 cfg.dev=&client->dev; cfg.of_node=client->dev.of_node; cfg.driver_data=map;
 cfg.init_data=of_get_regulator_init_data(&client->dev,client->dev.of_node,&desc);
 if(!cfg.init_data || !cfg.init_data->constraints.always_on)return -EINVAL;
 rdev=devm_regulator_register(&client->dev,&desc,&cfg);
 if(IS_ERR(rdev))return dev_err_probe(&client->dev,PTR_ERR(rdev),"Regulator registration failed\n");
 dev_info(&client->dev,"ALDO2 supply registered; compute supplies registered next\n");
 register_compute_supply(client,map,false);
 register_compute_supply(client,map,true);
 return 0;
}
static const struct of_device_id matches[] = {
 { .compatible="t95h,aldo2-only-test" }, {}
};
MODULE_DEVICE_TABLE(of,matches);
static struct i2c_driver t95h_aldo2_driver = {
 .driver={.name="t95h-aldo2-only",.of_match_table=matches}, .probe=supply_probe,
};
module_i2c_driver(t95h_aldo2_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("T95H late ALDO2, bounded DCDCA CPU DVFS, read-only DCDCC GPU supply");
