library(tidyverse)
library(ggthemes)

#setwd('~/Documents/GitHub/gcdl/documentation/multilayer_timings/')

datasets <- c("PRISM",
              "Daymet V4 (.tif)",
              "CRU (multiple .nc)", 
              "CRU (single .nc)",
              "Daymet V4 (.nc)")
approaches <- c("Per month and variable",
                "Per month and variable (point to file once)",
                "Per variable",
                "Per dataset")

tfiles <- list.files(".",
                     "timing_",
                     full.names = TRUE)
all_timings <- tibble()
for(file in tfiles){
  timings <- read_csv(file) %>%
    separate(test_id, c("approach","dataset","version","f_ext"), fill='right') %>%
    mutate(remote = ifelse(dataset == 5,"Remote","Local"),
           f_ext = ifelse(approach %in% 2:3 & !is.na(version), version, f_ext),
           version = ifelse(approach %in% 2:3 & !is.na(version), NA, version),
           dataset = ifelse(!is.na(f_ext), 5, dataset),
           dataset = factor(dataset, levels=1:5,
                            labels = datasets),
           version = ifelse(is.na(version),1,version)) %>%
    rowwise() %>%
    mutate(approach = paste(approach,version,sep="."),
           approach = factor(approach,
                             levels = c("1.1","1.2","2.1","3.1"),
                             labels = approaches)) %>%
    group_by(approach,dataset,num_years,remote) %>%
    summarise(time_sec_mean = mean(time_sec),
              time_sec_sd = sd(time_sec),
              N = n())
  
  all_timings <- all_timings %>%
    bind_rows(timings)
}


all_timings %>%
  ggplot(aes(num_years,time_sec_mean/60,color=approach)) +
  geom_line(aes(linetype=approach,group=paste(approach,remote)),
            size = 0.25) +
  geom_pointrange(aes(ymin = (time_sec_mean-time_sec_sd)/60,
                    ymax = (time_sec_mean+time_sec_sd)/60,
                    shape=remote),
                  #position = position_jitter(),
                size = 0.1,
                width = 0.25) +
  ylab("Processing time (minutes)") +
  xlab("No. data years processed") +
  theme_few(base_size = 8) +
  theme(legend.position = c(0.15,0.91),
        legend.text = element_text(size = 4),
        legend.title = element_text(size = 4),
        legend.background = element_blank(),
        legend.key.height = unit(0.1,'cm'),
        legend.spacing = unit(0,'cm')) +
  facet_wrap(~dataset) +
  scale_color_colorblind(name="Approach") +
  scale_linetype_discrete(name="Approach") +
  scale_shape_discrete(name='Data location') +
  scale_y_log10() +
  guides(shape = guide_legend(order = 2),
         linetype = guide_legend(order = 1),
         col = guide_legend(order = 1))
ggsave("xarray_timings.jpg",
       dpi = 300,
       units = 'in',
       height = 4,
       width = 6)


all_timings %>%
  mutate(time_sec = time_sec_mean/num_years) %>%
  ggplot(aes(num_years,time_sec,color=approach)) +
  geom_line(aes(linetype=approach,group=paste(approach,remote)),
            size = 0.25) +
  geom_point(aes(shape=remote),
             size = 1) +
  geom_errorbar(aes(ymin = (time_sec_mean-time_sec_sd)/num_years,
                    ymax = (time_sec_mean+time_sec_sd)/num_years),
                size = 0.25,
                width = 0.25) +
  ylab("Processing time (seconds/data year)") +
  xlab("No. data years processed") +
  theme_few(base_size = 8) +
  theme(legend.position = c(0.15,0.91),
        legend.text = element_text(size = 4),
        legend.title = element_text(size = 4),
        legend.background = element_blank(),
        legend.key.height = unit(0.1,'cm'),
        legend.spacing = unit(0,'cm')) +
  facet_wrap(~dataset) +
  scale_color_colorblind(name="Approach") +
  scale_linetype_discrete(name="Approach") +
  scale_shape_discrete(name='Data location') +
  scale_y_log10() +
  guides(shape = guide_legend(order = 2),
         linetype = guide_legend(order = 1),
         col = guide_legend(order = 1))
ggsave("xarray_timings_peryear.jpg",
       dpi = 300,
       units = 'in',
       height = 4,
       width = 6)


### Daymet comparison : .tif vs .nc
all_timings %>%
  filter(grepl("Daymet",dataset) & remote == "Local") %>%
  dplyr::select(-c(N,time_sec_sd)) %>%
  pivot_wider(names_from = dataset,
              values_from = time_sec_mean) %>%
  ggplot(aes(`Daymet V4 (.tif)`,`Daymet V4 (.nc)`)) +
  geom_abline() +
  geom_point(aes(color=approach),
             size = 1) +
  theme_few(base_size = 8) +
  theme(legend.position = c(0.35,0.65),
        legend.text = element_text(size = 4),
        legend.title = element_text(size = 4),
        legend.background = element_blank(),
        legend.key.height = unit(0.1,'cm'),
        legend.spacing = unit(0,'cm')) +
  facet_wrap(~approach) +
  scale_color_colorblind(name="Approach") 
ggsave("xarray_timings_localDaymet.jpg",
       dpi = 300,
       units = 'in',
       height = 4,
       width = 6)
